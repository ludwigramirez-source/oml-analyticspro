class AnalyticsRouter:
    """
    Enruta modelos managed=False con app_label 'analyticspro'
    a la BD 'analytics' (omnileads_local).
    Bloquea todas las operaciones de escritura.
    """
    APP_LABEL = 'analyticspro'
    DB_ALIAS = 'analytics'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return self.DB_ALIAS
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return None   # bloquear writes en modelos managed=False
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.APP_LABEL:
            return False   # no migraciones en BD analytics
        return None
