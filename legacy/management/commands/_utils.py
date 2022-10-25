def migrate_quotes():
    legacy_quotes = Sitater.objects.using("legacy").all()
    self.stdout.write(self.style.SUCCESS("Migrating legacy quotes to new table"))
    self.stdout.write(self.style.SUCCESS(f"Migrating {len(legacy_quotes)} quotes"))
    for (_, quote) in enumerate(legacy_quotes):
        self.stdout.write(self.style.SUCCESS(f"Migrerer sitat: {quote.tekst}"))
        LegacyQuote.objects.get_or_create(
            text=quote.tekst,
            datetime_created=quote.tid,
        )
    self.stdout.write(self.style.SUCCESS("Done migrating quotes"))
