from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.blog.models import Category, Comment, Post, PostStatus, Tag

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for local development"

    def handle(self, *args, **options):
        users_data = [
            ("alice@example.com", "Alice", "Johnson", "en", "UTC"),
            ("boris@example.com", "Boris", "Ivanov", "ru", "Europe/Moscow"),
            ("aidos@example.com", "Aidos", "Nurlan", "kk", "Asia/Almaty"),
        ]
        users = []
        for email, first_name, last_name, lang, tz in users_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "preferred_language": lang,
                    "timezone": tz,
                },
            )
            if created:
                user.set_password("Password123")
                user.save()
            users.append(user)

        categories_data = [
            ("Technology", "Технологии", "Технология", "technology"),
            ("Travel", "Путешествия", "Саяхат", "travel"),
            ("Food", "Еда", "Тағам", "food"),
        ]
        categories = []
        for name_en, name_ru, name_kk, slug in categories_data:
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_en": name_en, "name_ru": name_ru, "name_kk": name_kk},
            )
            categories.append(category)

        tags = []
        for name, slug in [
            ("django", "django"),
            ("python", "python"),
            ("api", "api"),
            ("redis", "redis"),
        ]:
            tag, _ = Tag.objects.get_or_create(name=name, slug=slug)
            tags.append(tag)

        for index in range(1, 13):
            post, _ = Post.objects.get_or_create(
                slug=f"demo-post-{index}",
                defaults={
                    "author": users[index % len(users)],
                    "title": f"Demo Post {index}",
                    "body": f"This is seeded demo post number {index}.",
                    "category": categories[index % len(categories)],
                    "status": PostStatus.PUBLISHED if index % 3 else PostStatus.DRAFT,
                },
            )
            post.tags.set(tags[: (index % len(tags)) + 1])
            if not post.comments.exists():
                for comment_index in range(1, 4):
                    Comment.objects.get_or_create(
                        post=post,
                        author=users[(index + comment_index) % len(users)],
                        body=f"Seeded comment {comment_index} for {post.slug}",
                    )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
