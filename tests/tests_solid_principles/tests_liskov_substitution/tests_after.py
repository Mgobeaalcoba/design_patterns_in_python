import unittest
import os
from typing import Protocol
from unittest.mock import patch
from faker import Faker
from src.solid_principles.liskov_substitution.after import *


class ContactInfoTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_contact_info_success(self):
        contact_info = ContactInfo(
            email=self.faker.email(),
            phone=self.faker.phone_number()
        )
        self.assertIsInstance(contact_info, ContactInfo)

    def test_contact_info_missing_email(self):
        contact_info = ContactInfo(
            phone=self.faker.phone_number()
        )
        self.assertIsInstance(contact_info, ContactInfo)

    def test_contact_info_missing_phone(self):
        contact_info = ContactInfo(
            email=self.faker.email()
        )
        self.assertIsInstance(contact_info, ContactInfo)

    def test_contact_info_missing_email_and_phone(self):
        contact_info = ContactInfo()
        self.assertIsInstance(contact_info, ContactInfo)


class CustomerDataTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_customer_data_success(self):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email(),
                phone=self.faker.phone_number()
            )
        )
        self.assertIsInstance(customer_data, CustomerData)

    def test_customer_data_missing_name(self):
        with self.assertRaises(ValueError):
            CustomerData(
                contact_info=ContactInfo(
                    email=self.faker.email(),
                    phone=self.faker.phone_number()
                )
            )

    def test_customer_data_missing_contact_info(self):
        with self.assertRaises(ValueError):
            CustomerData(
                name=self.faker.name()
            )

    def test_customer_data_missing_name_and_contact_info(self):
        with self.assertRaises(ValueError):
            CustomerData()


class PaymentDataTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_payment_data_success(self):
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        self.assertIsInstance(payment_data, PaymentData)

    def test_payment_data_missing_amount(self):
        with self.assertRaises(ValueError):
            PaymentData(
                source="tok_visa"
            )

    def test_payment_data_missing_source(self):
        with self.assertRaises(ValueError):
            PaymentData(
                amount=self.faker.random_number(digits=4)
            )

    def test_payment_data_missing_amount_and_source(self):
        with self.assertRaises(ValueError):
            PaymentData()

class NotifierProtocolTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def test_email_notifier_is_instance_of_notifier(self):
        email_notifier = EmailNotifier()
        self.assertIsInstance(email_notifier, Notifier)

    def test_sms_notifier_is_instance_of_notifier(self):
        sms_notifier = SMSNotifier()
        self.assertIsInstance(sms_notifier, Notifier)


class EmailNotifierTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.liskov_substitution.after.smtplib.SMTP')
    def test_send_confirmation_success(self, mock_smtp):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        email_notifier = EmailNotifier()
        email_notifier.send_confirmation(customer_data)
        mock_smtp.assert_called_once()
        mock_smtp.return_value.starttls.assert_called_once()
        mock_smtp.return_value.login.assert_called_once()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    @patch('src.solid_principles.liskov_substitution.after.smtplib.SMTP')
    def test_send_confirmation_email_failed(self, mock_smtp):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        email_notifier = EmailNotifier()
        mock_smtp.side_effect = Exception("Email failed")
        with self.assertRaises(Exception):
            email_notifier.send_confirmation(customer_data)


class SMSNotifierTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.liskov_substitution.after.Client')
    def test_send_confirmation_success(self, mock_client):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                phone=self.faker.phone_number()
            )
        )
        sms_notifier = SMSNotifier()
        sms_notifier.send_confirmation(customer_data)
        mock_client.assert_called_once()

    @patch('src.solid_principles.liskov_substitution.after.Client')
    def test_send_confirmation_sms_failed(self, mock_client):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                phone=self.faker.phone_number()
            )
        )
        sms_notifier = SMSNotifier()
        mock_client.return_value.messages.create.side_effect = Exception("SMS failed")
        with self.assertRaises(Exception):
            sms_notifier.send_confirmation(customer_data)


class TransactionLoggerTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.liskov_substitution.after.stripe.Charge')
    def test_log_transaction_success(self, mock_charge):
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        transaction_logger = TransactionLogger()
        transaction_logger.log(customer_data, payment_data, mock_charge)
        with open("transactions.log", "r") as log_file:
            logs = log_file.read()
            self.assertIn(f"{customer_data.name} paid {payment_data.amount}", logs)
            self.assertIn(f"Payment status: {mock_charge['status']}", logs)

    def tearDown(self):
        if os.path.exists("transactions.log"):
            os.remove("transactions.log")


class PaymentProcessorTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    def tests_stripe_payment_processor_is_instance_of_payment_processor(self):
        stripe_payment_processor = StripePaymentProcessor()
        self.assertIsInstance(stripe_payment_processor, PaymentProcessor)

class StripePaymentProcessorTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.liskov_substitution.after.stripe.Charge.create')
    def test_process_transaction_success(self, mock_charge):
        mock_charge.return_value = {"status": "succeeded"}
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        stripe_payment_processor = StripePaymentProcessor()
        charge = stripe_payment_processor.process_transaction(customer_data, payment_data)
        self.assertEqual(charge["status"], "succeeded")

    @patch('src.solid_principles.liskov_substitution.after.stripe.Charge.create')
    def test_process_transaction_failure(self, mock_charge):
        mock_charge.side_effect = StripeError("Payment failed")
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        stripe_payment_processor = StripePaymentProcessor()
        with self.assertRaises(StripeError):
            stripe_payment_processor.process_transaction(customer_data, payment_data)


class PaymentServiceTests(unittest.TestCase):

    def setUp(self):
        self.faker = Faker(locale="es_AR")

    @patch('src.solid_principles.liskov_substitution.after.smtplib.SMTP')
    @patch('src.solid_principles.liskov_substitution.after.stripe.Charge.create')
    def test_process_transaction_success(self, mock_charge, mock_smtp):
        mock_charge.return_value = {"status": "succeeded"}
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        payment_service = PaymentService()
        charge = payment_service.process_transaction(customer_data, payment_data)
        self.assertEqual(charge["status"], "succeeded")
        mock_smtp.assert_called_once()
        mock_smtp.return_value.starttls.assert_called_once()
        mock_smtp.return_value.login.assert_called_once()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    @patch('src.solid_principles.liskov_substitution.after.smtplib.SMTP')
    @patch('src.solid_principles.liskov_substitution.after.Client')
    @patch('src.solid_principles.liskov_substitution.after.stripe.Charge.create')
    def test_process_transaction_failure(self, mock_charge, mock_client, mock_smtp):
        mock_charge.side_effect = StripeError("Payment failed")
        customer_data = CustomerData(
            name=self.faker.name(),
            contact_info=ContactInfo(
                email=self.faker.email()
            )
        )
        payment_data = PaymentData(
            amount=self.faker.random_number(digits=4),
            source="tok_visa"
        )
        payment_service = PaymentService()
        with self.assertRaises(StripeError):
            payment_service.process_transaction(customer_data, payment_data)
        mock_client.assert_not_called()
        mock_smtp.assert_not_called()
        mock_smtp.return_value.starttls.assert_not_called()
        mock_smtp.return_value.login.assert_not_called()
        mock_smtp.return_value.sendmail.assert_not_called()
        mock_smtp.return_value.quit.assert_not_called()
