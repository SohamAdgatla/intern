"""Authentication helpers for session-based portal login."""
from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import PatientProfile, PatientUser, UserRole


def _serialize_user(user):
    profile = getattr(user, "profile", None)
    given_name = getattr(profile, "given_name", "") or ""
    family_name = getattr(profile, "family_name", "") or ""
    full_name = " ".join(part for part in [given_name.strip(), family_name.strip()] if part).strip()

    return {
        "id": user.id,
        "username": user.username,
        "role": getattr(user, "role", "patient"),
        "given_name": given_name.strip(),
        "family_name": family_name.strip(),
        "full_name": full_name or user.username,
    }


def _serialize_profile(user):
    data = _serialize_user(user)
    profile = getattr(user, "profile", None)
    if not profile:
        return data

    data.update(
        {
            "email_contact": profile.email_contact or "",
            "phone": profile.phone or "",
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "gender": profile.gender,
            "address_line": profile.address_line or "",
            "city": profile.city or "",
            "state": profile.state or "",
            "postal_code": profile.postal_code or "",
            "country": profile.country or "US",
        }
    )
    return data


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        given_name = request.data.get("given_name", "").strip()
        family_name = request.data.get("family_name", "").strip()

        if not username or not password or not given_name or not family_name:
            return Response(
                {"detail": "Username, password, first name, and last name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if PatientUser.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with that username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password)
        except ValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

        user = PatientUser.objects.create_user(
            username=username,
            password=password,
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=user,
            given_name=given_name,
            family_name=family_name,
        )

        login(request, user)
        return Response(_serialize_user(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(_serialize_user(user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_user(request.user))


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_profile(request.user))

    def patch(self, request):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        for field in [
            "given_name",
            "family_name",
            "phone",
            "email_contact",
            "birth_date",
            "gender",
            "address_line",
            "city",
            "state",
            "postal_code",
            "country",
        ]:
            value = request.data.get(field)
            if value is None:
                continue

            if field == "birth_date" and value:
                try:
                    profile.birth_date = value
                except ValueError:
                    return Response({"detail": "Invalid birth date."}, status=status.HTTP_400_BAD_REQUEST)
                continue

            if field in {"given_name", "family_name"} and isinstance(value, str):
                value = value.strip()
                if not value:
                    return Response({"detail": f"{field.replace('_', ' ').title()} is required."}, status=status.HTTP_400_BAD_REQUEST)

            setattr(profile, field, value)

        profile.save()
        return Response(_serialize_profile(request.user))
