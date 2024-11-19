"""
Module for payment processing, notifications, and transaction logging.

This module includes classes to handle payments using Stripe, send notifications via email or SMS,
and log transactions to a file. It also supports data simulation using `faker` and environment
variable configuration with `dotenv`.

Dependencies:
- os
- smtplib
- faker
- stripe
- twilio
- dotenv
- pydantic
"""
import os
import smtplib
import faker
import stripe

from twilio.rest import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from pydantic import BaseModel
from stripe import Charge
from stripe import StripeError

_ = load_dotenv()


class ContactInfo(BaseModel):
    """
    Pydantic model representing a customer's contact information.

    Attributes:
        email (Optional[str]): The customer's email address.
        phone (Optional[str]): The customer's phone number.
    """
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerData(BaseModel):
    """
    Pydantic model representing a customer's data.

    Attributes:
        name (str): The customer's full name.
        contact_info (ContactInfo): The customer's contact details.
    """
    name: str
    contact_info: ContactInfo


class PaymentData(BaseModel):
    """
    Pydantic model representing payment information.

    Attributes:
        amount (int): Payment amount in cents.
        source (str): The payment source (e.g., token or card ID).
    """
    amount: int
    source: str


class Notifier(ABC):
    """
    Abstract base class for notification services.
    """

    @abstractmethod
    def send_confirmation(self, customer_data: CustomerData):
        """
        Sends a confirmation message to the customer.

        Args:
            customer_data (CustomerData): The customer's data.
        """
        pass


class EmailNotifier(Notifier):
    """
    Concrete implementation of Notifier for sending email notifications.
    """

    def send_confirmation(self, customer_data: CustomerData):
        """
        Sends a payment confirmation email to the customer.

        Args:
            customer_data (CustomerData): The customer's data.

        Raises:
            Exception: If the email cannot be sent.
        """
        msg = MIMEMultipart()
        password = os.getenv("GMAIL_PASS")
        msg["From"] = "ethical.hacking.python@gmail.com"
        msg["To"] = customer_data.contact_info.email
        msg["Subject"] = "Payment Confirmation"
        msg.attach(MIMEText("The payment has been successful. Congrats!"))

        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.starttls()
            server.login(user=msg['From'], password=password)
            server.sendmail(from_addr=msg["From"], to_addrs=msg['To'], msg=msg.as_string())
            server.quit()
            print("Email successfully sent.")
        except Exception as e:
            print("Error while sending email:", e)


class SMSNotifier(Notifier):
    """
    Concrete implementation of Notifier for sending SMS notifications.
    """

    def send_confirmation(self, customer_data: CustomerData):
        """
        Sends a payment confirmation SMS to the customer.

        Args:
            customer_data (CustomerData): The customer's data.

        Raises:
            Exception: If the SMS cannot be sent.
        """
        sms_gateway = "Twilio"
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        try:
            message = client.messages.create(
                messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
                body='Ahoy 👋 Thank you for your payment!',
                to=customer_data.contact_info.phone,
            )
            print(
                f"SMS successfully sent to {customer_data.contact_info.phone} using {sms_gateway}. Message SID: {message.sid}")
        except Exception as e:
            print("Error while sending SMS:", e)


@dataclass
class TransactionLogger:
    """
    Handles transaction logging to a file.
    """

    @staticmethod
    def log(customer_data: CustomerData, payment_data: PaymentData, charge: Charge):
        """
        Logs transaction details to a file.

        Args:
            customer_data (CustomerData): The customer's data.
            payment_data (PaymentData): Payment details.
            charge (Charge): Stripe charge object containing transaction status.
        """
        with open("transactions.log", "a") as log_file:
            log_file.write(f"{customer_data.name} paid {payment_data.amount}\n")
            log_file.write(f"Payment status: {charge['status']}\n")


class PaymentProcessor(ABC):
    """
    Abstract base class for payment processors.
    """

    @abstractmethod
    def process_transaction(self, customer_data: CustomerData, payment_data: PaymentData) -> Charge:
        """
        Processes a payment transaction.

        Args:
            customer_data (CustomerData): The customer's data.
            payment_data (PaymentData): Payment details.

        Returns:
            Charge: A Stripe charge object representing the transaction.
        """
        pass


@dataclass
class StripePaymentProcessor(PaymentProcessor):
    """
    Concrete implementation of PaymentProcessor using Stripe API.
    """

    def process_transaction(self, customer_data: CustomerData, payment_data: PaymentData) -> Charge:
        """
        Processes a payment using the Stripe API.

        Args:
            customer_data (CustomerData): The customer's data.
            payment_data (PaymentData): Payment details.

        Returns:
            Charge: A Stripe charge object representing the transaction.

        Raises:
            StripeError: If the payment fails.
        """
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        try:
            charge = stripe.Charge.create(
                amount=payment_data.amount,
                currency="usd",
                source=payment_data.source,
                description="Charge for " + customer_data.name,
            )
            print("Payment successful")
            return charge
        except StripeError as e:
            print("Payment failed:", e)
            raise e


@dataclass
class PaymentService:
    """
    Service class that orchestrates payment processing, notifications, and logging.
    """
    payment_processor: PaymentProcessor = field(default_factory=StripePaymentProcessor)
    notifier: Notifier = field(default_factory=EmailNotifier)
    logger = TransactionLogger()

    def process_transaction(self, customer_data: CustomerData, payment_data: PaymentData) -> Charge:
        """
        Processes a payment, sends notifications, and logs the transaction.

        Args:
            customer_data (CustomerData): The customer's data.
            payment_data (PaymentData): Payment details.

        Returns:
            Charge: A Stripe charge object representing the transaction.

        Raises:
            StripeError: If the payment fails.
        """
        try:
            charge = self.payment_processor.process_transaction(
                customer_data, payment_data
            )
            self.notifier.send_confirmation(customer_data)
            self.logger.log(customer_data, payment_data, charge)
            return charge
        except StripeError as e:
            raise e


if __name__ == "__main__":
    """
    Example usage of the PaymentService to process transactions.
    """
    faker = faker.Faker(locale="es_AR")
    sms_notifier = SMSNotifier()
    payment_processor_sms = PaymentService(notifier=sms_notifier)
    payment_processor_email = PaymentService()

    customer_data_with_email = CustomerData(
        name=faker.name(),
        contact_info=ContactInfo(
            email="gobeamariano@gmail.com"
        )
    )
    customer_data_with_phone = CustomerData(
        name=faker.name(),
        contact_info=ContactInfo(
            phone="+5491138089556"
        )
    )

    payment_info = PaymentData(
        amount=faker.random_int(min=100, max=5000),
        source="tok_visa"
    )

    payment_processor_sms.process_transaction(customer_data_with_phone, payment_info)
    payment_processor_email.process_transaction(customer_data_with_email, payment_info)

    try:
        error_payment_data = PaymentData(
            amount=faker.random_int(min=100, max=5000),
            source="tok_radarBlock"
        )
        payment_processor_email.process_transaction(
            customer_data_with_email,
            error_payment_data
        )
    except Exception as err:
        print(f"Payment failed and PaymentProcessor raised an exception: {err}")
