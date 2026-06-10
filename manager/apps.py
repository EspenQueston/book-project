from django.apps import AppConfig


# 程序模块配置
class ManagerConfig(AppConfig):
    # 当在Django中定义一个没有指定主键的model时，Django将自动为您创建一个主键。
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'manager'
    
    def ready(self):
        """Import signals when app is ready"""
        import manager.signals  # noqa: F401
        import manager.escrow_signals  # noqa: F401
