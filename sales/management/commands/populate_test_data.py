from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
import random
from datetime import datetime, timedelta, date
from sales.models import Customer, Invoice, Quotation, Receipt, InvoiceItem, QuotationItem

class Command(BaseCommand):
    help = 'Populate database with test data using Faker'

    def add_arguments(self, parser):
        parser.add_argument('--customers', type=int, default=50, help='Number of customers to create')
        parser.add_argument('--quotations', type=int, default=80, help='Number of quotations to create')
        parser.add_argument('--invoices', type=int, default=120, help='Number of invoices to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')

    def handle(self, *args, **options):
        fake = Faker()
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Receipt.objects.all().delete()
            InvoiceItem.objects.all().delete()
            QuotationItem.objects.all().delete()
            Invoice.objects.all().delete()
            Quotation.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        
        # Create customers
        self.stdout.write('Creating customers...')
        customers = []
        for _ in range(options['customers']):
            customer = Customer.objects.create(
                name=fake.name(),
                email=fake.unique.email(),
                phone=fake.phone_number()[:20],
                address=fake.address(),
                company=fake.company() if random.choice([True, False]) else ''
            )
            customers.append(customer)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(customers)} customers'))
        
        # Product/Service catalog for line items
        products = [
            # IT Services
            ('Website Development', Decimal('2500.00'), Decimal('5000.00')),
            ('Mobile App Development', Decimal('5000.00'), Decimal('15000.00')),
            ('Database Design', Decimal('1200.00'), Decimal('3000.00')),
            ('System Integration', Decimal('1800.00'), Decimal('4500.00')),
            ('Cloud Migration', Decimal('3000.00'), Decimal('8000.00')),
            ('Security Audit', Decimal('2000.00'), Decimal('5000.00')),
            ('Software Maintenance', Decimal('500.00'), Decimal('2000.00')),
            ('Technical Support', Decimal('100.00'), Decimal('200.00')),
            ('Server Setup', Decimal('800.00'), Decimal('2500.00')),
            ('Data Analysis', Decimal('1500.00'), Decimal('4000.00')),
            
            # Consulting Services
            ('Business Analysis', Decimal('150.00'), Decimal('300.00')),
            ('Project Management', Decimal('120.00'), Decimal('250.00')),
            ('Strategic Planning', Decimal('200.00'), Decimal('400.00')),
            ('Process Optimization', Decimal('180.00'), Decimal('350.00')),
            ('Training Sessions', Decimal('100.00'), Decimal('200.00')),
            ('Compliance Review', Decimal('250.00'), Decimal('500.00')),
            ('Risk Assessment', Decimal('220.00'), Decimal('450.00')),
            ('Market Research', Decimal('300.00'), Decimal('800.00')),
            ('Financial Planning', Decimal('200.00'), Decimal('500.00')),
            ('Operations Review', Decimal('180.00'), Decimal('400.00')),
            
            # Products
            ('Software License', Decimal('50.00'), Decimal('500.00')),
            ('Hardware Equipment', Decimal('200.00'), Decimal('2000.00')),
            ('Network Equipment', Decimal('300.00'), Decimal('1500.00')),
            ('Security Software', Decimal('100.00'), Decimal('800.00')),
            ('Backup Solution', Decimal('80.00'), Decimal('400.00')),
            ('Monitoring Tools', Decimal('60.00'), Decimal('300.00')),
            ('Development Tools', Decimal('40.00'), Decimal('200.00')),
            ('Office Software', Decimal('25.00'), Decimal('150.00')),
            ('Antivirus Software', Decimal('30.00'), Decimal('100.00')),
            ('Cloud Storage', Decimal('20.00'), Decimal('200.00')),
            
            # Marketing Services
            ('Social Media Management', Decimal('800.00'), Decimal('2500.00')),
            ('Content Creation', Decimal('500.00'), Decimal('1500.00')),
            ('SEO Optimization', Decimal('600.00'), Decimal('2000.00')),
            ('Email Marketing', Decimal('400.00'), Decimal('1200.00')),
            ('Brand Design', Decimal('1000.00'), Decimal('5000.00')),
            ('Video Production', Decimal('1500.00'), Decimal('8000.00')),
            ('Photography', Decimal('300.00'), Decimal('1500.00')),
            ('Print Design', Decimal('200.00'), Decimal('800.00')),
            ('Website Analytics', Decimal('250.00'), Decimal('600.00')),
            ('Marketing Strategy', Decimal('1200.00'), Decimal('4000.00')),
            
            # Arabic Services (from the image)
            ('خدمات تطوير المواقع', Decimal('2000.00'), Decimal('6000.00')),
            ('تصميم الجرافيك', Decimal('300.00'), Decimal('1200.00')),
            ('الاستشارات التقنية', Decimal('150.00'), Decimal('400.00')),
            ('إدارة المشاريع', Decimal('120.00'), Decimal('300.00')),
            ('التدريب والتطوير', Decimal('100.00'), Decimal('250.00')),
            ('خدمات الترجمة', Decimal('50.00'), Decimal('200.00')),
            ('تحليل البيانات', Decimal('800.00'), Decimal('2500.00')),
            ('الأمن السيبراني', Decimal('1500.00'), Decimal('5000.00')),
            ('التسويق الرقمي', Decimal('600.00'), Decimal('2000.00')),
            ('إدارة المحتوى', Decimal('400.00'), Decimal('1200.00')),
        ]
        
        # Create quotations
        self.stdout.write('Creating quotations...')
        quotations = []
        for i in range(options['quotations']):
            customer = random.choice(customers)
            quotation_date = fake.date_between(start_date='-6M', end_date='today')
            valid_until = quotation_date + timedelta(days=random.randint(30, 90))
            
            # Auto-generate quotation number
            quotation_number = f"QT-{(i+1):05d}"
            
            quotation = Quotation.objects.create(
                quotation_number=quotation_number,
                customer=customer,
                created_by=admin_user,
                status=random.choices(
                    ['draft', 'sent', 'accepted', 'rejected', 'expired'],
                    weights=[10, 30, 25, 15, 20]
                )[0],
                quotation_date=quotation_date,
                valid_until=valid_until,
                tax_rate=Decimal(random.choice([0, 5, 10, 15])),
                notes=fake.text(max_nb_chars=200) if random.choice([True, False]) else ''
            )
            
            # Add items to quotation
            num_items = random.randint(1, 8)
            subtotal = Decimal('0')
            
            for _ in range(num_items):
                product_name, min_price, max_price = random.choice(products)
                quantity = Decimal(str(random.uniform(1, 10))).quantize(Decimal('0.01'))
                unit_price = Decimal(str(random.uniform(float(min_price), float(max_price)))).quantize(Decimal('0.01'))
                line_total = quantity * unit_price
                
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=product_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total
                )
                subtotal += line_total
            
            # Update totals
            quotation.subtotal = subtotal
            quotation.tax_amount = subtotal * (quotation.tax_rate / 100)
            quotation.total_amount = quotation.subtotal + quotation.tax_amount
            quotation.save()
            
            quotations.append(quotation)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(quotations)} quotations'))
        
        # Create invoices (some from quotations, some standalone)
        self.stdout.write('Creating invoices...')
        invoices = []
        accepted_quotations = [q for q in quotations if q.status == 'accepted']
        
        for i in range(options['invoices']):
            customer = random.choice(customers)
            
            # 40% chance to create from accepted quotation
            source_quotation = None
            if accepted_quotations and random.random() < 0.4:
                source_quotation = random.choice(accepted_quotations)
                customer = source_quotation.customer
                accepted_quotations.remove(source_quotation)  # Don't reuse
            
            invoice_date = fake.date_between(start_date='-4M', end_date='today')
            due_date = invoice_date + timedelta(days=random.randint(15, 60))
            
            # Determine status based on dates and randomness
            today = date.today()
            if due_date < today:
                status = random.choices(['paid', 'overdue'], weights=[60, 40])[0]
            else:
                status = random.choices(['draft', 'sent', 'paid'], weights=[10, 40, 50])[0]
            
            invoice_number = f"INV-{(i+1):05d}"
            
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                quotation=source_quotation,
                created_by=admin_user,
                status=status,
                invoice_date=invoice_date,
                due_date=due_date,
                tax_rate=source_quotation.tax_rate if source_quotation else Decimal(random.choice([0, 5, 10, 15])),
                notes=fake.text(max_nb_chars=200) if random.choice([True, False]) else ''
            )
            
            subtotal = Decimal('0')
            
            if source_quotation:
                # Copy items from quotation
                for q_item in source_quotation.items.all():
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=q_item.description,
                        quantity=q_item.quantity,
                        unit_price=q_item.unit_price,
                        line_total=q_item.line_total
                    )
                    subtotal += q_item.line_total
            else:
                # Create new items
                num_items = random.randint(1, 6)
                for _ in range(num_items):
                    product_name, min_price, max_price = random.choice(products)
                    quantity = Decimal(str(random.uniform(1, 8))).quantize(Decimal('0.01'))
                    unit_price = Decimal(str(random.uniform(float(min_price), float(max_price)))).quantize(Decimal('0.01'))
                    line_total = quantity * unit_price
                    
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=product_name,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total
                    )
                    subtotal += line_total
            
            # Update totals
            invoice.subtotal = subtotal
            invoice.tax_amount = subtotal * (invoice.tax_rate / 100)
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            invoice.save()
            
            invoices.append(invoice)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(invoices)} invoices'))
        
        # Create receipts for paid and partially paid invoices
        self.stdout.write('Creating receipts...')
        receipts_created = 0
        
        payment_methods = ['cash', 'card', 'bank_transfer', 'check', 'online']
        
        for invoice in invoices:
            if invoice.status in ['paid', 'overdue']:
                # Fully paid invoices
                if invoice.status == 'paid':
                    # 80% chance of single payment, 20% multiple payments
                    if random.random() < 0.8:
                        # Single payment
                        receipt_date = invoice.invoice_date + timedelta(
                            days=random.randint(1, (invoice.due_date - invoice.invoice_date).days + 30)
                        )
                        receipt_number = f"REC-{receipts_created + 1:05d}"
                        
                        Receipt.objects.create(
                            receipt_number=receipt_number,
                            invoice=invoice,
                            customer=invoice.customer,
                            amount=invoice.total_amount,
                            payment_method=random.choice(payment_methods),
                            payment_date=receipt_date,
                            reference_number=fake.bothify('REF-####-????') if random.choice([True, False]) else '',
                            notes=fake.text(max_nb_chars=100) if random.choice([True, False]) else '',
                            created_by=admin_user
                        )
                        
                        invoice.paid_amount = invoice.total_amount
                        invoice.save()
                        receipts_created += 1
                    else:
                        # Multiple payments
                        remaining_amount = invoice.total_amount
                        payment_count = random.randint(2, 4)
                        
                        for p in range(payment_count):
                            if remaining_amount <= 0:
                                break
                                
                            if p == payment_count - 1:
                                # Final payment
                                payment_amount = remaining_amount
                            else:
                                # Partial payment (20-60% of remaining)
                                payment_amount = remaining_amount * Decimal(str(random.uniform(0.2, 0.6))).quantize(Decimal('0.01'))
                            
                            receipt_date = invoice.invoice_date + timedelta(
                                days=random.randint(p * 5 + 1, p * 15 + 30)
                            )
                            
                            receipt_number = f"REC-{receipts_created + 1:05d}"
                            
                            Receipt.objects.create(
                                receipt_number=receipt_number,
                                invoice=invoice,
                                customer=invoice.customer,
                                amount=payment_amount,
                                payment_method=random.choice(payment_methods),
                                payment_date=receipt_date,
                                reference_number=fake.bothify('REF-####-????') if random.choice([True, False]) else '',
                                notes=f'Partial payment {p+1}/{payment_count}' if payment_count > 1 else '',
                                created_by=admin_user
                            )
                            
                            remaining_amount -= payment_amount
                            receipts_created += 1
                        
                        invoice.paid_amount = invoice.total_amount - remaining_amount
                        invoice.save()
                
                elif invoice.status == 'overdue':
                    # Overdue invoices - 60% have partial payments
                    if random.random() < 0.6:
                        # Partial payment
                        partial_percentage = random.uniform(0.1, 0.8)
                        payment_amount = invoice.total_amount * Decimal(str(partial_percentage)).quantize(Decimal('0.01'))
                        
                        receipt_date = invoice.invoice_date + timedelta(
                            days=random.randint(1, (date.today() - invoice.invoice_date).days)
                        )
                        
                        receipt_number = f"REC-{receipts_created + 1:05d}"
                        
                        Receipt.objects.create(
                            receipt_number=receipt_number,
                            invoice=invoice,
                            customer=invoice.customer,
                            amount=payment_amount,
                            payment_method=random.choice(payment_methods),
                            payment_date=receipt_date,
                            reference_number=fake.bothify('REF-####-????') if random.choice([True, False]) else '',
                            notes='Partial payment - balance overdue',
                            created_by=admin_user
                        )
                        
                        invoice.paid_amount = payment_amount
                        invoice.save()
                        receipts_created += 1
            
            elif invoice.status == 'sent':
                # 30% of sent invoices have partial payments
                if random.random() < 0.3:
                    partial_percentage = random.uniform(0.2, 0.7)
                    payment_amount = invoice.total_amount * Decimal(str(partial_percentage)).quantize(Decimal('0.01'))
                    
                    receipt_date = invoice.invoice_date + timedelta(
                        days=random.randint(1, min(30, (date.today() - invoice.invoice_date).days))
                    )
                    
                    receipt_number = f"REC-{receipts_created + 1:05d}"
                    
                    Receipt.objects.create(
                        receipt_number=receipt_number,
                        invoice=invoice,
                        customer=invoice.customer,
                        amount=payment_amount,
                        payment_method=random.choice(payment_methods),
                        payment_date=receipt_date,
                        reference_number=fake.bothify('REF-####-????') if random.choice([True, False]) else '',
                        notes='Partial payment received',
                        created_by=admin_user
                    )
                    
                    invoice.paid_amount = payment_amount
                    invoice.save()
                    receipts_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {receipts_created} receipts'))
        
        # Summary statistics
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('TEST DATA GENERATION COMPLETE'))
        self.stdout.write('='*50)
        
        # Customers summary
        total_customers = Customer.objects.count()
        self.stdout.write(f'📋 Customers: {total_customers}')
        
        # Quotations summary
        total_quotations = Quotation.objects.count()
        quotation_stats = {
            'draft': Quotation.objects.filter(status='draft').count(),
            'sent': Quotation.objects.filter(status='sent').count(),
            'accepted': Quotation.objects.filter(status='accepted').count(),
            'rejected': Quotation.objects.filter(status='rejected').count(),
            'expired': Quotation.objects.filter(status='expired').count(),
        }
        self.stdout.write(f'📄 Quotations: {total_quotations} total')
        for status, count in quotation_stats.items():
            self.stdout.write(f'   - {status}: {count}')
        
        # Invoices summary
        total_invoices = Invoice.objects.count()
        invoice_stats = {
            'draft': Invoice.objects.filter(status='draft').count(),
            'sent': Invoice.objects.filter(status='sent').count(),
            'paid': Invoice.objects.filter(status='paid').count(),
            'overdue': Invoice.objects.filter(status='overdue').count(),
        }
        self.stdout.write(f'🧾 Invoices: {total_invoices} total')
        for status, count in invoice_stats.items():
            self.stdout.write(f'   - {status}: {count}')
        
        # Financial summary
        from django.db.models import Sum
        total_invoice_amount = Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_paid_amount = Invoice.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
        total_outstanding = total_invoice_amount - total_paid_amount
        
        self.stdout.write(f'💰 Financial Summary:')
        self.stdout.write(f'   - Total Invoice Amount: {total_invoice_amount:,.2f} QAR')
        self.stdout.write(f'   - Total Paid Amount: {total_paid_amount:,.2f} QAR')
        self.stdout.write(f'   - Outstanding Receivables: {total_outstanding:,.2f} QAR')
        
        # Receipts summary
        total_receipts = Receipt.objects.count()
        self.stdout.write(f'🧾 Receipts: {total_receipts} payment records')
        
        self.stdout.write('='*50)
        self.stdout.write(self.style.SUCCESS('✨ Ready for testing! Visit http://localhost:8010/'))
        self.stdout.write('='*50)