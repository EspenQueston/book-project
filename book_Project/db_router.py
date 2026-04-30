class MarketplaceRouter:
    """
    Database router that directs marketplace app queries to the 'marketplace' database
    and everything else to the 'default' database.
    """
    marketplace_app = 'marketplace'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.marketplace_app:
            return 'marketplace'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.marketplace_app:
            return 'marketplace'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations within the same database
        db1 = 'marketplace' if obj1._meta.app_label == self.marketplace_app else 'default'
        db2 = 'marketplace' if obj2._meta.app_label == self.marketplace_app else 'default'
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.marketplace_app:
            return db == 'marketplace'
        # Don't migrate non-marketplace apps to the marketplace database
        if db == 'marketplace':
            return False
        return None
