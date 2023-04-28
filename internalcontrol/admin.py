from django.contrib import admin
from .models import (
    InternalControlDocument,
    InternalControlDocumentItem,
    InternalControlDocumentItemCollection,
    InternalControlDocumentTemplate,
    InternalControlDocumentTemplateItem,
    InternalControlDocumentItemCollectionTemplate,
)


class InternalControlDocumentTemplateItemAdmin(admin.ModelAdmin):
    pass


class InternalControlDocumentItemInline(admin.TabularInline):
    model = InternalControlDocumentItem
    extra = 0


class InternalControlDocumentItemCollectionInline(admin.TabularInline):
    model = InternalControlDocumentItemCollection
    extra = 0


class InternalControlDocumentAdmin(admin.ModelAdmin):
    inlines = [InternalControlDocumentItemCollectionInline]


class InternalControlDocumentItemCollectionAdmin(admin.ModelAdmin):
    inlines = [InternalControlDocumentItemInline]


class InternalControlDocumentTemplateItemInline(admin.TabularInline):

    model = InternalControlDocumentTemplateItem
    extra = 0


class InternalControlDocumentItemCollectionTemplateInline(admin.TabularInline):

    model = InternalControlDocumentItemCollectionTemplate
    extra = 0


class InternalControlDocumentTemplateAdmin(admin.ModelAdmin):
    inlines = [InternalControlDocumentItemCollectionTemplateInline]


class InternalControlDocumentItemCollectionTemplateAdmin(admin.ModelAdmin):
    inlines = [InternalControlDocumentTemplateItemInline]


admin.site.register(InternalControlDocument, InternalControlDocumentAdmin)
admin.site.register(
    InternalControlDocumentItemCollection, InternalControlDocumentItemCollectionAdmin
)
admin.site.register(
    InternalControlDocumentTemplate, InternalControlDocumentTemplateAdmin
)
admin.site.register(
    InternalControlDocumentItemCollectionTemplate,
    InternalControlDocumentItemCollectionTemplateAdmin,
)
admin.site.register(
    InternalControlDocumentTemplateItem, InternalControlDocumentTemplateItemAdmin
)
