import unittest
import os
from unittest.mock import patch
from faker import Faker
from stripe import StripeError
from src.solid_principles.initial_code import PaymentProcessor


class PaymentProcessorTests(unittest.TestCase):

    def setUp(self):
        self.payment_processor = PaymentProcessor()
        self.faker = Faker(locale="es_AR")

    # Test that the process_transaction method returns None when the customer_data is missing the name key
    def test_process_transaction_missing_name(self):
        customer_data = {"contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the process_transaction method returns None when the customer_data is missing the contact_info key
    def test_process_transaction_missing_contact_info(self):
        customer_data = {"name": self.faker.name()}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the process_transaction method returns None when the payment_data is missing the source key
    def test_process_transaction_missing_source(self):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the stripe.Charge.create raises an StripeError and the process_transaction method returns None
    @patch('src.solid_principles.initial_code.stripe.Charge.create')
    def test_process_transaction_payment_failed(self, mock_charge):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_charge.side_effect = StripeError("Payment failed")
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the process_transaction method sends an email to the customer when the payment is successful
    @patch('src.solid_principles.initial_code.smtplib.SMTP')
    def test_process_transaction_payment_successful(self, mock_smtp):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))
        mock_smtp.assert_called_once()
        mock_smtp.return_value.starttls.assert_called_once()
        mock_smtp.return_value.login.assert_called_once()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    # Test that the process_transaction method try to send an email but the SMTPlib raises an exception
    @patch('src.solid_principles.initial_code.smtplib.SMTP')
    def test_process_transaction_email_failed(self, mock_smtp):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_smtp.side_effect = Exception("Email failed")
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the process_transaction method sends an sms to the customer when the payment is successful
    @patch('src.solid_principles.initial_code.Client')
    def test_process_transaction_payment_successful_sms(self, mock_client):
        customer_data = {"name": self.faker.name(), "contact_info": {"phone": self.faker.phone_number()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))
        mock_client.assert_called_once()
        mock_client.return_value.messages.create.assert_called_once()

    # Test that the process_transaction method try to send an sms but the Twilio raises an exception
    @patch('src.solid_principles.initial_code.Client')
    def test_process_transaction_sms_failed(self, mock_client):
        customer_data = {"name": self.faker.name(), "contact_info": {"phone": self.faker.phone_number()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_client.return_value.messages.create.side_effect = Exception("SMS failed")
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))
        mock_client.assert_called_once()

    # Test that the contact_info is not an email or phone number
    def test_process_transaction_invalid_contact_info(self):
        customer_data = {"name": self.faker.name(), "contact_info": {"address": self.faker.address()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))
        self.assertEqual(self.payment_processor.process_transaction(customer_data, payment_data), None)

    # Delete the "transactions.log" file post test execution
    def tearDown(self):
        if os.path.exists("transactions.log"):
            os.remove("transactions.log")
