from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import Department
from inventory.models import AssetCategory, InventoryItem, AssetAllocation

class InventoryTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='Officer'
        )
        self.teacher = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='Staff', user_type=UserRole.TEACHER
        )

        self.cat = AssetCategory.objects.create(name='IT Equipment')
        self.item = InventoryItem.objects.create(
            item_code='IT-LAP-001',
            name='Dell Latitude 5420 Laptop',
            category=self.cat,
            quantity_total=10,
            quantity_in_use=2,
            unit='Pieces',
            reorder_threshold=3,
            cost_per_unit=Decimal('800.00'),
            location='IT Storage'
        )

    def test_inventory_item_availability_and_valuation(self):
        """Verify available quantity and asset monetary valuation calculations"""
        self.assertEqual(self.item.available_quantity, 8)
        self.assertFalse(self.item.is_low_stock)
        self.assertEqual(self.item.total_asset_value, Decimal('8000.00'))

    def test_asset_allocation_and_return_workflow(self):
        """Verify allocating asset to teacher increases in-use counter and return decrements it"""
        self.client.login(email='admin@school.edu', password=self.password)
        
        # 1. Allocate 3 laptops
        response = self.client.post(reverse('inventory:allocation_create'), {
            'item': str(self.item.id),
            'allocated_to_user': str(self.teacher.id),
            'quantity': 3,
            'allocated_date': timezone.now().date().strftime('%Y-%m-%d'),
            'notes': 'Faculty teaching laptop',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_in_use, 5)
        self.assertEqual(self.item.available_quantity, 5)

        allocation = AssetAllocation.objects.filter(item=self.item, allocated_to_user=self.teacher).first()
        self.assertIsNotNone(allocation)
        self.assertEqual(allocation.status, AssetAllocation.Status.ACTIVE)

        # 2. Return the 3 laptops
        resp_ret = self.client.post(reverse('inventory:allocation_return', kwargs={'pk': allocation.pk}), follow=True)
        self.assertEqual(resp_ret.status_code, 200)

        allocation.refresh_from_db()
        self.assertEqual(allocation.status, AssetAllocation.Status.RETURNED)

        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_in_use, 2)
        self.assertEqual(self.item.available_quantity, 8)
