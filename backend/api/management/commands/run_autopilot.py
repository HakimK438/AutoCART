from django.core.management.base import BaseCommand

from api.automation import sweep


class Command(BaseCommand):
    help = "Autopilot catch-up: pack every waiting order whose sellers turned on 'pack new orders for me'. Safe to run as often as you like (cron, Task Scheduler)."

    def handle(self, *args, **options):
        self.stdout.write(f'{sweep()} order(s) packed by autopilot.')
