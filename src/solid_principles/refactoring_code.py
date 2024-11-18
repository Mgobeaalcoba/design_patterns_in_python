"""
Module: Payment Processor

This module provides a class `PaymentProcessor` for processing customer payments
using Stripe for payment transactions, Twilio for SMS notifications,
and Gmail SMTP for email confirmations. It handles errors gracefully and logs
transaction details for audit purposes.
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
    @staticmethod
    def validate(customer_data):
        """
        Validates customer data.

        Args:
            customer_data (dict): Contains customer details.

        Returns:
            None
        """
        if not customer_data.get("name"):
            raise ValueError("Invalid customer data")
        if not customer_data.get("contact_info"):
            raise ValueError("Invalid customer data")


@dataclass
class ValidatedPaymentData:
    @staticmethod
    def validate(payment_data):
        """
        Validates payment data.

        Args:
            payment_data (dict): Contains payment details.

        Returns:
            None
        """
        if not payment_data.get("source"):
            raise ValueError("Invalid payment data")


@dataclass
class NotificationSender:
    @staticmethod
    def send_email_notification(email):
        """
        Sends a payment confirmation email.

        Args:
            email (str): Recipient's email address.

        Returns:
            None
        """
        msg = MIMEMultipart()
        password = os.getenv("GMAIL_PASS")
        print(f'Password: {password}')  # Debugging the password variable
        msg["From"] = "ethical.hacking.python@gmail.com"
        msg["To"] = email
        msg["Subject"] = "Payment Confirmation"
        msg.attach(MIMEText("The payment has been successful. Congrats!"))

        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.starttls()
            print("Server started")
            server.login(user=msg['From'], password=password)
            print("Server logged in")
            server.sendmail(from_addr=msg["From"], to_addrs=msg['To'], msg=msg.as_string())
            print("Email sent")
            server.quit()
        except Exception as e:
            print("Error sending email: ", e)

    @staticmethod
    def send_sms_notification(phone):
        """
        Sends a payment confirmation SMS.

        Args:
            phone (str): Recipient's phone number.

        Returns:
            None
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
            print(f"SMS sent to {phone}: Thank you for your payment.")
            print(message.sid)
        except Exception as e:
            print("Error sending SMS:", e)


@dataclass
class TransactionLogger:
    @staticmethod
    def log_transaction(customer_data, payment_data, charge):
        """
        Logs the transaction details to a file.

        Args:
            customer_data (dict): Customer details.
            payment_data (dict): Payment details.
            charge (dict): Stripe charge details.

        Returns:
            None
        """
        with open("transactions.log", "a") as log_file:
            log_file.write(
                f"{customer_data['name']} paid {payment_data['amount']} cents\n"
            )
            log_file.write(f"Payment status: {charge['status']}\n")


@dataclass
class StripePaymentProcessor:
    """
    Handles the processing of payments and customer notifications.

    This class uses:
    - Stripe for payment processing
    - Gmail SMTP for email notifications
    - Twilio for SMS notifications

    Methods:
        process_transaction(customer_data, payment_data):
            Validates data, processes the payment, sends notifications,
            and logs transaction details.
    """

    @staticmethod
    def process_transaction(customer_data, payment_data) -> Charge:
        """
        Processes a customer payment and sends notifications.

        Args:
            customer_data (dict): Contains customer details:
                - name (str): Customer's name.
                - contact_info (dict): Notification details, can include:
                    - email (str): Customer's email address.
                    - phone (str): Customer's phone number.
            payment_data (dict): Contains payment details:
                - amount (int): Payment amount in cents (e.g., 100 = $1.00).
                - source (str): Stripe token for the payment source.

        Returns:
            None: Logs errors or confirmation messages to the console.
        """
        # Configure Stripe API
        stripe.api_key = os.getenv("STRIPE_API_KEY")

        try:
            # Process the payment using Stripe
            charge = stripe.Charge.create(
                amount=payment_data["amount"],
                currency="usd",
                source=payment_data["source"],
                description="Charge for " + customer_data["name"],
            )
            print("Payment successful")
        except StripeError as e:
            print("Payment failed:", e)
            raise e

        return charge


@dataclass
class PaymentService:
    customer_validator = ValidatedCustomerData()
    payment_validator = ValidatedPaymentData()
    payment_processor = StripePaymentProcessor()
    notifier = NotificationSender()
    logger = TransactionLogger()

    def process_transaction(self, customer_data, payment_data) -> Charge:
        try:
            self.customer_validator.validate(customer_data)
            self.payment_validator.validate(payment_data)
            charge = self.payment_processor.process_transaction(customer_data, payment_data)
            if customer_data["contact_info"].get("email"):
                self.notifier.send_email_notification(customer_data["contact_info"].get("email"))
            elif customer_data["contact_info"].get("phone"):
                self.notifier.send_sms_notification(customer_data["contact_info"].get("phone"))
            else:
                print("No valid contact info provided")
            self.logger.log_transaction(customer_data, payment_data, charge)
            return charge
        except Exception as e:
            print(e)


if __name__ == "__main__":
    # Example usage of the PaymentProcessor class
    payment_processor = PaymentService()

    # Customer with email notification
    customer_data_with_email = {
        "name": faker.name(),
        "contact_info": {"email": "gobeamariano@gmail.com"},
    }

    # Customer with SMS notification
    customer_data_with_phone = {
        "name": faker.name(),
        "contact_info": {"phone": "+5491138089556"},
    }

    # Example payment data
    payment_data_email = {"amount": faker.random_int(min=100, max=20000), "source": "tok_mastercard"}
    payment_data_phone = {"amount": faker.random_int(min=100, max=20000), "source": "tok_visa"}

    # Process transactions
    payment_processor.process_transaction(customer_data_with_email, payment_data_email)
    payment_processor.process_transaction(customer_data_with_phone, payment_data_phone)
