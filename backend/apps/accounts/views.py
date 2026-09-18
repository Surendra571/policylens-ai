from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """Register a new user account and return JWT credentials."""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Authenticate with email and password to obtain JWT tokens."""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        tokens = serializer.validated_data["tokens"]
        return Response(
            {
                "success": True,
                "message": "Authentication successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )
    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Retrieve details of the currently authenticated user."""
    serializer = UserSerializer(request.user)
    return Response(
        {
            "success": True,
            "user": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


# Placeholder status view for backward compatibility
@api_view(["GET"])
@permission_classes([AllowAny])
def accounts_status(request):
    return Response({"module": "accounts", "status": "initialized"}, status=status.HTTP_200_OK)
