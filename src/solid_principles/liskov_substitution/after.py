# The before.py in this package is the after.py of open_close package.
"""
Module for payment processing, notifications, and transaction logging.

This module provides classes for managing payments via the Stripe API, sending notifications through email or SMS,
and logging transaction details into a file. It also integrates tools for data simulation (`faker`) and environment
variable configuration (`dotenv`), supporting a wide range of use cases for payment workflows.

Key Features:
- **Payment Processing**: Facilitates secure and customizable payment processing via the Stripe API.
- **Notifications**: Enables sending payment confirmations via email (SMTP) and SMS (Twilio).
- **Logging**: Records transaction details, ensuring traceability.
- **Data Simulation**: Uses `faker` for generating test data.
- **Environment Management**: Leverages `dotenv` to manage sensitive credentials securely.

Dependencies:
- `os`: For environment variable access.
- `smtplib`: For sending email notifications.
- `faker`: For generating random test data.
- `stripe`: For payment processing.
- `twilio`: For SMS notifications.
- `dotenv`: For environment configuration.
- `pydantic`: For validating and managing structured data.

Usage:
This module is designed to be flexible and modular, supporting extensibility for additional payment gateways or notification systems.
"""
import os
import smtplib
import faker
import stripe

from twilio.rest import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable
from dotenv import load_dotenv
from pydantic import BaseModel
from stripe import Charge
from stripe import StripeError

_ = load_dotenv()


class ContactInfo(BaseModel):
    """
    Pydantic model representing a customer's contact information.

    Attributes:
        email (Optional[str]): The customer's email address. Defaults to `None` if not provided.
        phone (Optional[str]): The customer's phone number. Defaults to `None` if not provided.

    Example:
        contact = ContactInfo(email="user@example.com", phone="+123456789")
    """
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerData(BaseModel):
    """
    Pydantic model representing a customer's data.

    Attributes:
        name (str): The customer's full name.
        contact_info (ContactInfo): An instance of `ContactInfo` containing the customer's email and phone details.

    Example:
        customer = CustomerData(
            name="John Doe",
            contact_info=ContactInfo(email="john.doe@example.com", phone="+123456789")
        )
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

@runtime_checkable
class Notifier(Protocol):
    """
    Protocol for sending notifications to customers post-payment.

    Implementing classes must define a `send_confirmation` method, which sends a message to the provided customer.
    """

    def send_confirmation(self, customer_data: CustomerData):
        """
        Sends a confirmation message to the customer.

        Args:
            customer_data (CustomerData): The customer's data.
        """
        ...


class EmailNotifier(Notifier):
    """
    Notifier implementation for sending payment confirmation emails.

    Notes:
        - Requires a Gmail account configured via environment variables for authentication (`GMAIL_PASS`).
        - The email is sent through Gmail's SMTP server.

    Raises:
        Exception: If email delivery fails due to network issues or invalid configuration.

    Example:
        notifier = EmailNotifier()
        notifier.send_confirmation(customer_data)
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
            raise e


@dataclass
class SMSNotifier(Notifier):
    """
    Notifier implementation for sending SMS notifications.
    """
    sms_gateway: str = "Twilio"

    def send_confirmation(self, customer_data: CustomerData):
        """
        Sends a payment confirmation SMS to the customer.

        Args:
            customer_data (CustomerData): The customer's data.

        Raises:
            Exception: If the SMS cannot be sent.
        """
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
                f"SMS successfully sent to {customer_data.contact_info.phone} using {self.sms_gateway}. Message SID: {message.sid}")
        except Exception as e:
            print("Error while sending SMS:", e)
            raise e


@dataclass
class TransactionLogger:
    """
    Handles logging transaction details to a file for audit and debugging purposes.

    Notes:
        - Logs are appended to a file named `transactions.log` in the current directory.
        - The log includes customer name, payment amount, and payment status.

    Example:
        logger = TransactionLogger()
        logger.log(customer_data, payment_data, charge)
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

@runtime_checkable
class PaymentProcessor(Protocol):
    """
    Protocol for processing payment transactions.

    This protocol defines the method signature for processing a payment transaction.
    """

    def process_transaction(self, customer_data: CustomerData, payment_data: PaymentData):
        """
        Processes a payment transaction.

        Args:
            customer_data (CustomerData): The customer's data.
            payment_data (PaymentData): Payment details.

        Returns:
            Charge: A Stripe charge object representing the transaction.
        """
        ...


@dataclass
class StripePaymentProcessor(PaymentProcessor):
    """
    Concrete implementation of `PaymentProcessor` using the Stripe API.

    Notes:
        - Requires a valid Stripe API key (`STRIPE_API_KEY`) set in the environment.
        - Processes payments in USD by default.

    Raises:
        StripeError: If the payment fails due to invalid tokens, insufficient funds, or other issues.

    Example:
        processor = StripePaymentProcessor()
        charge = processor.process_transaction(customer_data, payment_data)
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
    Service class that orchestrates payment processing, notifications, and transaction logging.

    Attributes:
        payment_processor (PaymentProcessor): Instance of a class implementing `PaymentProcessor`.
        notifier (Notifier): Instance of a class implementing `Notifier`.
        logger (TransactionLogger): Static class for logging transaction details.

    Methods:
        process_transaction: Processes a payment, notifies the customer, and logs the transaction.

    Example:
        service = PaymentService()
        charge = service.process_transaction(customer_data, payment_data)
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
    sms_notifier = SMSNotifier(sms_gateway="Twilio")
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
