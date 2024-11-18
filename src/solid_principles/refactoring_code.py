"""
Module: Payment Processor

This module provides functionality for processing customer payments using the Stripe API,
sending email notifications via Gmail's SMTP service, and sending SMS notifications through Twilio.
It also validates customer and payment data, handles errors gracefully, and logs transaction details.

Classes:
    ValidatedCustomerData: Validates customer information before processing.
    ValidatedPaymentData: Validates payment information for required fields.
    NotificationSender: Handles sending notifications via email or SMS.
    TransactionLogger: Logs transaction details for record-keeping.
    StripePaymentProcessor: Processes payments using Stripe API.
    PaymentService: Integrates validation, payment processing, notifications, and logging.
"""

import os
import smtplib
import faker
import stripe

from stripe import StripeError, Charge
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from dataclasses import dataclass

# Load environment variables
_ = load_dotenv(override=True)

# Initialize Faker with an Argentine locale
faker = faker.Faker(locale="es_AR")


@dataclass
class ValidatedCustomerData:
    """
    A utility class to validate customer data for required fields.
    """

    @staticmethod
    def validate(customer_data):
        """
        Validates customer data to ensure required fields are present.

        Args:
            customer_data (dict): Contains customer details.

        Raises:
            ValueError: If required fields are missing.
        """
        if not customer_data.get("name"):
            raise ValueError("Customer data validation failed: Missing name.")
        if not customer_data.get("contact_info"):
            raise ValueError("Customer data validation failed: Missing contact info.")


@dataclass
class ValidatedPaymentData:
    """
    A utility class to validate payment data for required fields.
    """

    @staticmethod
    def validate(payment_data):
        """
        Validates payment data to ensure required fields are present.

        Args:
            payment_data (dict): Contains payment details.

        Raises:
            ValueError: If required fields are missing.
        """
        if not payment_data.get("source"):
            raise ValueError("Payment data validation failed: Missing source.")


@dataclass
class NotificationSender:
    """
    A utility class for sending notifications via email or SMS.
    """

    @staticmethod
    def send_email_notification(email):
        """
        Sends a payment confirmation email.

        Args:
            email (str): Recipient's email address.

        Logs:
            Sends an email with a payment confirmation message.
        """
        msg = MIMEMultipart()
        password = os.getenv("GMAIL_PASS")
        msg["From"] = "ethical.hacking.python@gmail.com"
        msg["To"] = email
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

    @staticmethod
    def send_sms_notification(phone):
        """
        Sends a payment confirmation SMS.

        Args:
            phone (str): Recipient's phone number.

        Logs:
            Sends an SMS with a payment confirmation message.
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        try:
            message = client.messages.create(
                messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
                body='Ahoy 👋 Thank you for your payment!',
                to=phone,
            )
            print(f"SMS successfully sent to {phone}. Message SID: {message.sid}")
        except Exception as e:
            print("Error while sending SMS:", e)


@dataclass
class TransactionLogger:
    """
    A utility class for logging transaction details to a file.
    """

    @staticmethod
    def log_transaction(customer_data, payment_data, charge):
        """
        Logs the transaction details to a file.

        Args:
            customer_data (dict): Customer details.
            payment_data (dict): Payment details.
            charge (dict): Stripe charge response.

        Writes:
            Logs transaction details to 'transactions.log'.
        """
        with open("transactions.log", "a") as log_file:
            log_file.write(
                f"{customer_data['name']} paid {payment_data['amount']} cents\n"
            )
            log_file.write(f"Payment status: {charge['status']}\n")


@dataclass
class StripePaymentProcessor:
    """
    Handles Stripe payment processing.
    """

    @staticmethod
    def process_transaction(customer_data, payment_data) -> Charge:
        """
        Processes a customer payment using the Stripe API.

        Args:
            customer_data (dict): Customer details.
            payment_data (dict): Payment details.

        Returns:
            Charge: The Stripe charge object.

        Raises:
            StripeError: If the payment fails.
        """
        stripe.api_key = os.getenv("STRIPE_API_KEY")

        try:
            charge = stripe.Charge.create(
                amount=payment_data["amount"],
                currency="usd",
                source=payment_data["source"],
                description=f"Charge for {customer_data['name']}",
            )
            print("Payment processed successfully.")
            return charge
        except StripeError as e:
            print("Payment processing failed:", e)
            raise e


@dataclass
class PaymentService:
    """
    Integrates all components for processing payments and notifications.
    """

    customer_validator = ValidatedCustomerData()
    payment_validator = ValidatedPaymentData()
    payment_processor = StripePaymentProcessor()
    notifier = NotificationSender()
    logger = TransactionLogger()

    def process_transaction(self, customer_data, payment_data) -> None:
        """
        Orchestrates the payment processing workflow.

        Args:
            customer_data (dict): Customer details.
            payment_data (dict): Payment details.

        Logs:
            Validates data, processes payments, sends notifications, and logs transactions.
        """
        try:
            self.customer_validator.validate(customer_data)
            self.payment_validator.validate(payment_data)
            charge = self.payment_processor.process_transaction(customer_data, payment_data)

            if email := customer_data["contact_info"].get("email"):
                self.notifier.send_email_notification(email)
            elif phone := customer_data["contact_info"].get("phone"):
                self.notifier.send_sms_notification(phone)
            else:
                print("No valid contact info provided.")

            self.logger.log_transaction(customer_data, payment_data, charge)
        except Exception as e:
            print("Transaction processing failed:", e)


if __name__ == "__main__":
    # Example usage of PaymentService
    payment_service = PaymentService()

    customer_data_with_email = {
        "name": faker.name(),
        "contact_info": {"email": "example@gmail.com"},
    }
    customer_data_with_phone = {
        "name": faker.name(),
        "contact_info": {"phone": "+1234567890"},
    }

    payment_data_email = {"amount": 1000, "source": "tok_mastercard"}
    payment_data_phone = {"amount": 1500, "source": "tok_visa"}

    payment_service.process_transaction(customer_data_with_email, payment_data_email)
    payment_service.process_transaction(customer_data_with_phone, payment_data_phone)
