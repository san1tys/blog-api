from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.blog.models import Category, Comment, Post, PostStatus, Tag

User = get_user_model()

# ---------------------------------------------------------------------------
# Fixture data — mirrors what scripts/start.sh seeded in hw2
# ---------------------------------------------------------------------------

SUPERUSER = {
    "email": "admin@example.com",
    "password": "Admin12345",
    "first_name": "Admin",
    "last_name": "User",
}

USERS = [
    ("alice@example.com", "Alice", "Johnson", "en", "UTC"),
    ("boris@example.com", "Boris", "Ivanov", "ru", "Europe/Moscow"),
    ("aidos@example.com", "Aidos", "Nurlan", "kk", "Asia/Almaty"),
]

CATEGORIES = [
    ("Technology", "Технологии", "Технология", "technology"),
    ("Travel", "Путешествия", "Саяхат", "travel"),
    ("Food", "Еда", "Тағам", "food"),
]

TAGS = [
    ("django", "django"),
    ("python", "python"),
    ("api", "api"),
    ("redis", "redis"),
]


class Command(BaseCommand):
    help = "Seed the database with demo data (idempotent). Mirrors hw2 start.sh."

    def handle(self, *args, **options):
        self._seed_superuser()
        users = self._seed_users()
        categories = self._seed_categories()
        tags = self._seed_tags()
        self._seed_posts(users, categories, tags)
        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _seed_superuser(self):
        email = SUPERUSER["email"]
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=SUPERUSER["password"],
                first_name=SUPERUSER["first_name"],
                last_name=SUPERUSER["last_name"],
            )
            self.stdout.write(f"  Created superuser: {email}")

    def _seed_users(self):
        users = []
        for email, first_name, last_name, lang, tz in USERS:
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
                self.stdout.write(f"  Created user: {email}")
            users.append(user)
        return users

    def _seed_categories(self):
        categories = []
        for name_en, name_ru, name_kk, slug in CATEGORIES:
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_en": name_en, "name_ru": name_ru, "name_kk": name_kk},
            )
            if created:
                self.stdout.write(f"  Created category: {slug}")
            categories.append(category)
        return categories

    def _seed_tags(self):
        tags = []
        for name, slug in TAGS:
            tag, created = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            if created:
                self.stdout.write(f"  Created tag: {slug}")
            tags.append(tag)
        return tags

    def _seed_posts(self, users, categories, tags):
        for i in range(1, 13):
            post, created = Post.objects.get_or_create(
                slug=f"demo-post-{i}",
                defaults={
                    "author": users[i % len(users)],
                    "title": f"Demo Post {i}",
                    "body": f"This is seeded demo post number {i}.",
                    "category": categories[i % len(categories)],
                    "status": PostStatus.PUBLISHED if i % 3 else PostStatus.DRAFT,
                },
            )
            post.tags.set(tags[: (i % len(tags)) + 1])
            if created:
                self.stdout.write(f"  Created post: {post.slug}")
            self._seed_comments(post, users, i)

    def _seed_comments(self, post, users, post_index):
        for j in range(1, 4):
            author = users[(post_index + j) % len(users)]
            _, created = Comment.objects.get_or_create(
                post=post,
                author=author,
                body=f"Seeded comment {j} for {post.slug}.",
            )
            if created:
                self.stdout.write(f"    Created comment {j} on {post.slug}")
