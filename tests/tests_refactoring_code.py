import unittest
import os
from unittest.mock import patch
from faker import Faker
from stripe import StripeError, Charge
from src.solid_principles.refactoring_code import *


class PaymentProcessorTests(unittest.TestCase):

    def setUp(self):
        self.payment_processor = PaymentService()
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
    @patch('src.solid_principles.refactoring_code.stripe.Charge.create')
    def test_process_transaction_payment_failed(self, mock_charge):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_charge.side_effect = StripeError("Payment failed")
        self.assertIsNone(self.payment_processor.process_transaction(customer_data, payment_data))

    # Test that the process_transaction method sends an email to the customer when the payment is successful
    @patch('src.solid_principles.refactoring_code.smtplib.SMTP')
    def test_process_transaction_payment_successful(self, mock_smtp):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsInstance(self.payment_processor.process_transaction(customer_data, payment_data), Charge)
        mock_smtp.assert_called_once()
        mock_smtp.return_value.starttls.assert_called_once()
        mock_smtp.return_value.login.assert_called_once()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    # Test that the process_transaction method try to send an email but the SMTPlib raises an exception
    @patch('src.solid_principles.refactoring_code.smtplib.SMTP')
    def test_process_transaction_email_failed(self, mock_smtp):
        customer_data = {"name": self.faker.name(), "contact_info": {"email": self.faker.email()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_smtp.side_effect = Exception("Email failed")
        self.assertIsInstance(self.payment_processor.process_transaction(customer_data, payment_data), Charge)
        mock_smtp.assert_called_once()

    # Test that the process_transaction method sends an SMS to the customer when the payment is successful
    @patch('src.solid_principles.refactoring_code.Client')
    def test_process_transaction_sms_successful(self, mock_client):
        customer_data = {"name": self.faker.name(), "contact_info": {"phone": self.faker.phone_number()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsInstance(self.payment_processor.process_transaction(customer_data, payment_data), Charge)
        mock_client.assert_called_once()
        mock_client.return_value.messages.create.assert_called_once()

    # Test that the process_transaction method try to send an SMS but the twilio raises an exception
    @patch('src.solid_principles.refactoring_code.Client')
    def test_process_transaction_sms_failed(self, mock_client):
        customer_data = {"name": self.faker.name(), "contact_info": {"phone": self.faker.phone_number()}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        mock_client.return_value.messages.create.side_effect = Exception("SMS failed")
        self.assertIsInstance(self.payment_processor.process_transaction(customer_data, payment_data), Charge)
        mock_client.assert_called_once()
        mock_client.return_value.messages.create.assert_called_once()

    # Test when the transaction have no valid contact info
    def test_process_transaction_no_valid_contact_info(self):
        customer_data = {"name": self.faker.name(), "contact_info": {"address": "123 Main St"}}
        payment_data = {"amount": self.faker.random_number(digits=4), "source": "tok_visa", "cvv": 345}
        self.assertIsInstance(self.payment_processor.process_transaction(customer_data, payment_data), Charge)

    def tearDown(self):
        if os.path.exists("transactions.log"):
            os.remove("transactions.log")
