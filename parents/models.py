import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class ParentProfile(BaseModel):
    """
    Parent / Guardian Profile linked to a User account.
    A single parent can have multiple linked students across different grades.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100, blank=True)
    mother_name = models.CharField(max_length=100, blank=True)
    
    occupation = models.CharField(max_length=100, blank=True)
    annual_income = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    primary_phone = models.CharField(max_length=50)
    secondary_phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    residential_address = models.TextField()

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = _('Parent / Guardian Profile')
        verbose_name_plural = _('Parent / Guardian Profiles')

    def __str__(self):
        return f"{self.full_name} ({self.primary_phone})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def children(self):
        return [relation.student for relation in self.linked_students.select_related('student')]


class ParentStudent(BaseModel):
    """
    Many-to-Many Relationship model between ParentProfile and Student.
    Defines specific relationship type and guardian authorization privileges.
    """
    class RelationshipType(models.TextChoices):
        FATHER = 'FATHER', _('Father')
        MOTHER = 'MOTHER', _('Mother')
        LEGAL_GUARDIAN = 'LEGAL_GUARDIAN', _('Legal Guardian')
        GRANDPARENT = 'GRANDPARENT', _('Grandparent')
        FOSTER = 'FOSTER', _('Foster Parent')
        OTHER = 'OTHER', _('Other')

    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='linked_students')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='parent_relations')
    relationship_type = models.CharField(max_length=30, choices=RelationshipType.choices, default=RelationshipType.FATHER)
    is_primary_contact = models.BooleanField(default=True, help_text=_('Designates primary SMS alert contact'))
    can_pickup_child = models.BooleanField(default=True, help_text=_('Authorized to pick up child from campus'))

    class Meta:
        unique_together = ('parent', 'student')
        verbose_name = _('Parent-Student Link')
        verbose_name_plural = _('Parent-Student Links')

    def __str__(self):
        return f"{self.parent.full_name} ({self.get_relationship_type_display()}) -> {self.student.full_name}"
