from __future__ import unicode_literals

import re

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator, )
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.managers import InheritanceManager


# Create your models here.
class CategoryManager(models.Manager):
    def new_category(self, category):
        new_category = self.create(category=re.sub('\s+', '-', category).lower())

        new_category.save()
        return new_category


class Category(models.Model):
    category_name = models.CharField(
        verbose_name="Category",
        max_length=250,
        blank=True,
        unique=True,
        null=True
    )

    objects = CategoryManager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.category_name


class SubCategory(models.Model):
    sub_category_name = models.CharField(
        verbose_name="Sub-Category",
        max_length=250, blank=True, null=True)

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        verbose_name="Category",
        on_delete=models.CASCADE)

    objects = CategoryManager()

    class Meta:
        verbose_name = "Sub-Category"
        verbose_name_plural = "Sub-Categories"

    def __str__(self):
        return self.sub_category_name + " (" + self.category.category_name + ")"


class Quiz(models.Model):
    title = models.CharField(
        verbose_name="Title",
        max_length=60,
        blank=False
    )

    description = models.TextField(
        verbose_name="Description",
        blank=True,
        help_text="A description of the quiz."
    )

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        verbose_name="Category",
        on_delete=models.CASCADE
    )

    random_order = models.BooleanField(
        blank=False,
        default=False,
        verbose_name="Random Order",
        help_text="Display the questions in a random order or as they are set?"
    )

    max_questions = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Max Questions",
        help_text="Number of questions to be answered on each attempt."
    )

    answers_at_end = models.BooleanField(
        blank=False,
        default=False,
        help_text="Correct answer is NOT shown after question. Answers displayed at the end.",
        verbose_name="Answers at end"
    )

    store_answers = models.BooleanField(
        blank=False,
        default=False,
        help_text="If yes, the results of each attempt by a user will be stored.",
        verbose_name="Store Answers"
    )

    single_attempt = models.BooleanField(
        blank=False,
        default=False,
        help_text="If yes, only one attempt by a user will be permitted.",
        verbose_name="Single Attempt"
    )

    pass_mark = models.SmallIntegerField(
        blank=True,
        default=0,
        verbose_name="Pass Mark",
        help_text="Percentage required to pass exam.",
        validators=[MaxValueValidator(100)]
    )

    success_text = models.TextField(
        blank=True,
        help_text="Displayed if user passes.",
        verbose_name="Success Text"
    )

    fail_text = models.TextField(
        verbose_name="Fail Text",
        blank=True, help_text="Displayed if user fails."
    )

    draft = models.BooleanField(
        blank=True,
        default=False,
        verbose_name="Draft",
        help_text="If yes, the quiz is not displayed in the quiz list and can only be taken by users who can edit quizzes."
    )

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.pass_mark > 100:
            raise ValidationError('%s is above 100' % self.pass_mark)

        super(Quiz, self).save(force_insert, force_update, *args, **kwargs)

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    def get_questions(self):
        return self.question_set.all().select_subclasses()

    @property
    def get_max_score(self):
        return self.get_questions().count()


class Question(models.Model):
    """
    Base class for all question types.
    Shared properties placed here.
    """

    quiz = models.ManyToManyField(
        Quiz,
        verbose_name="Quiz",
        blank=True
    )

    category = models.ForeignKey(
        Category,
        verbose_name="Category",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    sub_category = models.ForeignKey(
        SubCategory,
        verbose_name="Sub-Category",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    content = models.CharField(
        max_length=1000,
        blank=False,
        help_text="Enter the question text that you want displayed",
        verbose_name='Question'
    )

    explanation = models.TextField(
        max_length=2000,
        blank=True,
        help_text="Explanation to be shown after the question has been answered.",
        verbose_name='Explanation'
    )

    objects = InheritanceManager()

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['category']

    def __str__(self):
        return self.content
