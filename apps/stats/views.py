from __future__ import annotations

import asyncio

import httpx
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from apps.blog.models import Post, Comment

User = get_user_model()

EXCHANGE_URL = "https://open.er-api.com/v6/latest/USD"
TIME_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty"


async def fetch_exchange_rates(client: httpx.AsyncClient) -> dict:
    response = await client.get(EXCHANGE_URL, timeout=10.0)
    response.raise_for_status()
    data = response.json()
    rates = data["rates"]

    return {
        "KZT": rates["KZT"],
        "RUB": rates["RUB"],
        "EUR": rates["EUR"],
    }


async def fetch_current_time(client: httpx.AsyncClient) -> str:
    response = await client.get(TIME_URL, timeout=10.0)
    response.raise_for_status()
    data = response.json()
    return data["dateTime"]


async def build_stats_payload() -> dict:
    total_posts = await sync_to_async(Post.objects.count)()
    total_comments = await sync_to_async(Comment.objects.count)()
    total_users = await sync_to_async(User.objects.count)()

    async with httpx.AsyncClient() as client:
        exchange_rates, current_time = await asyncio.gather(
            fetch_exchange_rates(client),
            fetch_current_time(client),
        )

    return {
        "blog": {
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_users": total_users,
        },
        "exchange_rates": exchange_rates,
        "current_time": current_time,
    }


class StatsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Stats"],
        summary="Get combined blogs and external statistics",
        description="Returns blog counts from the local database and combines them with data from two public APIs.",
        responses={
            200: OpenApiResponse(description="Combined statistics payload"),
            429: OpenApiResponse(description="Throttle limit exceeded"),
        },
        examples=[
            OpenApiExample(
                "Stats responce",
                value={
                    "blog": {
                        "total_posts": 100,
                        "total_comments": 250,
                        "total_users": 50,
                    },
                    "exchange_rates": {"KZT": 470.0, "RUB": 75.0, "EUR": 0.85},
                    "current_time": "2024-06-01T12:00:00",
                },
                response_only=True,
                status_codes=["200"],
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        data = asyncio.run(build_stats_payload())
        return Response(data)
