from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.group_chat.models import Membership

class Command(BaseCommand):
    help = '🧹 Dọn dẹp các bản ghi Membership bị trùng lặp cho cùng một cặp user và group.'

    def handle(self, *args, **options):
        duplicates = (
            Membership.objects.values('user', 'group')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_deleted = 0
        for entry in duplicates:
            user_id = entry['user']
            group_id = entry['group']

            memberships = Membership.objects.filter(user_id=user_id, group_id=group_id).order_by('-id')
            redundant_ids = [m.id for m in memberships[1:]]

            deleted_count, _ = Membership.objects.filter(id__in=redundant_ids).delete()
            total_deleted += deleted_count

        self.stdout.write(
            self.style.SUCCESS(f'✨ Đã dọn dẹp thành công! Đã xóa {total_deleted} bản ghi Membership dư thừa.')
        )

# python manage.py cleanup_memberships