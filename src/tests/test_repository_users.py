import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository import users as repository_users


# ================== GET USER TESTS ==================
@pytest.mark.asyncio
async def test_get_user_by_username_exists(
    db_session: AsyncSession,
    user_data
):
    # Create test user
    user = User(**user_data.dict())
    db_session.add(user)
    await db_session.commit()

    # Get user by username
    found_user = await repository_users.get_user_by_username(
        user_data.username,
        db_session
    )
    assert found_user is not None
    assert found_user.username == user_data.username
    assert found_user.email == user_data.email


@pytest.mark.asyncio
async def test_get_user_by_username_not_exists(db_session: AsyncSession):
    found_user = await repository_users.get_user_by_username(
        "nonexistent",
        db_session
    )
    assert found_user is None


@pytest.mark.asyncio
async def test_get_user_by_email_exists(
    db_session: AsyncSession,
    user_data
):
    # Create test user
    user = User(**user_data.dict())
    db_session.add(user)
    await db_session.commit()

    # Get user by email
    found_user = await repository_users.get_user_by_email(
        user_data.email,
        db_session
    )
    assert found_user is not None
    assert found_user.username == user_data.username
    assert found_user.email == user_data.email


@pytest.mark.asyncio
async def test_get_user_by_email_not_exists(db_session: AsyncSession):
    found_user = await repository_users.get_user_by_email(
        "nonexistent@example.com",
        db_session
    )
    assert found_user is None


@pytest.mark.asyncio
async def test_get_user_by_id_exists(
    db_session: AsyncSession,
    user_data
):
    # Create test user
    user = User(**user_data.dict())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Get user by id
    found_user = await repository_users.get_user_by_id(user.id, db_session)
    assert found_user is not None
    assert found_user.username == user_data.username
    assert found_user.email == user_data.email


@pytest.mark.asyncio
async def test_get_user_by_id_not_exists(db_session: AsyncSession):
    found_user = await repository_users.get_user_by_id(999, db_session)
    assert found_user is None


# ================== GET USERS TESTS ==================
@pytest.mark.asyncio
async def test_get_users_empty(db_session: AsyncSession):
    users = await repository_users.get_users(db_session)
    assert len(users) == 0


@pytest.mark.asyncio
async def test_get_users_with_pagination(
    db_session: AsyncSession,
    user_data
):
    # Create test users
    for i in range(15):
        user = User(
            username=f"{user_data.username}{i}",
            email=f"user{i}@example.com",
            password=user_data.password,
            full_name=f"User {i}"
        )
        db_session.add(user)
    await db_session.commit()

    # Test pagination
    users_page1 = await repository_users.get_users(
        db_session,
        skip=0,
        limit=10
    )
    assert len(users_page1) == 10

    users_page2 = await repository_users.get_users(
        db_session,
        skip=10,
        limit=10
    )
    assert len(users_page2) == 5

    # Verify no overlap between pages
    page1_usernames = {user.username for user in users_page1}
    page2_usernames = {user.username for user in users_page2}
    assert not page1_usernames.intersection(page2_usernames)


@pytest.mark.asyncio
async def test_get_users_filter_by_username(
    db_session: AsyncSession,
    user_data
):
    # Create test users
    test_username = "testuser"
    for i in range(3):
        user = User(
            username=f"{test_username}{i}",
            email=f"user{i}@example.com",
            password=user_data.password,
            full_name=f"User {i}"
        )
        db_session.add(user)
    # Add one user with different username
    other_user = User(
        username="otheruser",
        email="other@example.com",
        password=user_data.password,
        full_name="Other User"
    )
    db_session.add(other_user)
    await db_session.commit()

    # Test filtering by username
    filtered_users = await repository_users.get_users(
        db_session,
        username=test_username
    )
    assert len(filtered_users) == 3
    assert all(test_username in user.username for user in filtered_users)


@pytest.mark.asyncio
async def test_get_users_filter_by_email(
    db_session: AsyncSession,
    user_data
):
    # Create test users
    test_email_domain = "testdomain.com"
    for i in range(3):
        user = User(
            username=f"user{i}",
            email=f"user{i}@{test_email_domain}",
            password=user_data.password,
            full_name=f"User {i}"
        )
        db_session.add(user)
    # Add one user with different email domain
    other_user = User(
        username="otheruser",
        email="other@example.com",
        password=user_data.password,
        full_name="Other User"
    )
    db_session.add(other_user)
    await db_session.commit()

    # Test filtering by email
    filtered_users = await repository_users.get_users(
        db_session,
        email=test_email_domain
    )
    assert len(filtered_users) == 3
    assert all(test_email_domain in user.email for user in filtered_users)


@pytest.mark.asyncio
async def test_get_users_filter_by_id(
    db_session: AsyncSession,
    user_data
):
    # Create test user
    user = User(**user_data.dict())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create additional users
    for i in range(3):
        other_user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password=user_data.password,
            full_name=f"User {i}"
        )
        db_session.add(other_user)
    await db_session.commit()

    # Test filtering by id
    filtered_users = await repository_users.get_users(
        db_session,
        user_id=user.id
    )
    assert len(filtered_users) == 1
    assert filtered_users[0].id == user.id
    assert filtered_users[0].username == user_data.username


# ================== COUNT ACTIVE ADMINS TESTS ==================
@pytest.mark.asyncio
async def test_count_active_admins_empty(db_session: AsyncSession):
    count = await repository_users.count_active_admins(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_count_active_admins_with_admins(
    db_session: AsyncSession,
    user_data
):
    # Create active admins
    for i in range(3):
        user = User(
            username=f"admin{i}",
            email=f"admin{i}@example.com",
            password=user_data.password,
            full_name=f"Admin {i}",
            is_admin=True,
            is_active=True
        )
        db_session.add(user)

    # Create inactive admin
    inactive_admin = User(
        username="inactive_admin",
        email="inactive@example.com",
        password=user_data.password,
        full_name="Inactive Admin",
        is_admin=True,
        is_active=False
    )
    db_session.add(inactive_admin)

    # Create active non-admin
    non_admin = User(
        username="non_admin",
        email="user@example.com",
        password=user_data.password,
        full_name="Regular User",
        is_admin=False,
        is_active=True
    )
    db_session.add(non_admin)

    await db_session.commit()

    count = await repository_users.count_active_admins(db_session)
    assert count == 3


# ================== CREATE USER AND UPDATE TOKEN TESTS ==================
@pytest.mark.asyncio
async def test_create_user_success(
    db_session: AsyncSession,
    user_data
):
    user = await repository_users.create_user(user_data, db_session)
    assert user.id is not None
    assert user.username == user_data.username
    assert user.email == user_data.email
    assert user.password == user_data.password
    assert user.full_name == user_data.full_name
    assert not user.is_admin
    assert user.is_active
    assert not user.confirmed
    assert user.refresh_token is None


@pytest.mark.asyncio
async def test_update_token_set_token(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    assert user.refresh_token is None

    # Set refresh token
    test_token = "test_refresh_token"
    await repository_users.update_token(user, test_token, db_session)

    # Verify token was set
    updated_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert updated_user.refresh_token == test_token


@pytest.mark.asyncio
async def test_update_token_clear_token(
    db_session: AsyncSession,
    user_data
):
    # Create user with token
    user = await repository_users.create_user(user_data, db_session)
    test_token = "test_refresh_token"
    await repository_users.update_token(user, test_token, db_session)

    # Clear token
    await repository_users.update_token(user, None, db_session)

    # Verify token was cleared
    updated_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert updated_user.refresh_token is None


@pytest.mark.asyncio
async def test_update_token_update_existing(
    db_session: AsyncSession,
    user_data
):
    # Create user with token
    user = await repository_users.create_user(user_data, db_session)
    old_token = "old_refresh_token"
    await repository_users.update_token(user, old_token, db_session)

    # Update token
    new_token = "new_refresh_token"
    await repository_users.update_token(user, new_token, db_session)

    # Verify token was updated
    updated_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert updated_user.refresh_token == new_token


# ================== CONFIRM EMAIL AND UPDATE PROFILE TESTS ==================
@pytest.mark.asyncio
async def test_confirmed_email_success(
    db_session: AsyncSession,
    user_data
):
    # Create unconfirmed user
    user = await repository_users.create_user(user_data, db_session)
    assert not user.confirmed

    # Confirm email
    await repository_users.confirmed_email(user.email, db_session)

    # Verify email was confirmed
    updated_user = await repository_users.get_user_by_email(
        user.email,
        db_session
    )
    assert updated_user.confirmed


@pytest.mark.asyncio
async def test_confirmed_email_nonexistent_email(db_session: AsyncSession):
    # Try to confirm nonexistent email
    await repository_users.confirmed_email(
        "nonexistent@example.com",
        db_session
    )
    # Should not raise any exception


@pytest.mark.asyncio
async def test_confirmed_email_already_confirmed(
    db_session: AsyncSession,
    user_data
):
    # Create confirmed user
    user = await repository_users.create_user(user_data, db_session)
    await repository_users.confirmed_email(user.email, db_session)
    assert user.confirmed

    # Try to confirm again
    await repository_users.confirmed_email(user.email, db_session)
    # Should not raise any exception


@pytest.mark.asyncio
async def test_update_profile_full_update(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)

    # Update profile
    new_data = {
        "full_name": "New Name",
        "email": "newemail@example.com"
    }
    updated_user = await repository_users.update_profile(
        user,
        full_name=new_data["full_name"],
        email=new_data["email"],
        db=db_session
    )

    # Verify updates
    assert updated_user.full_name == new_data["full_name"]
    assert updated_user.email == new_data["email"]
    # Verify other fields unchanged
    assert updated_user.username == user_data.username
    assert updated_user.password == user_data.password


@pytest.mark.asyncio
async def test_update_profile_partial_update(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    original_email = user.email

    # Update only full_name
    new_full_name = "New Name"
    updated_user = await repository_users.update_profile(
        user,
        full_name=new_full_name,
        db=db_session
    )

    # Verify only full_name was updated
    assert updated_user.full_name == new_full_name
    assert updated_user.email == original_email


@pytest.mark.asyncio
async def test_update_profile_no_changes(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    original_state = {
        "email": user.email,
        "full_name": user.full_name
    }

    # Update with None values
    updated_user = await repository_users.update_profile(
        user,
        email=None,
        full_name=None,
        db=db_session
    )

    # Verify no changes
    assert updated_user.email == original_state["email"]
    assert updated_user.full_name == original_state["full_name"]


# ================== UPDATE PASSWORD TESTS ==================
@pytest.mark.asyncio
async def test_update_password_success(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    original_password = user.password

    # Update password
    new_password = "NewHashedPass123!"
    await repository_users.update_password(
        user.username,
        new_password,
        db_session
    )

    # Verify password was updated
    updated_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert updated_user.password == new_password
    assert updated_user.password != original_password


@pytest.mark.asyncio
async def test_update_password_nonexistent_user(db_session: AsyncSession):
    with pytest.raises(ValueError, match="Użytkownik nie istnieje"):
        await repository_users.update_password(
            "nonexistent",
            "NewPass123!",
            db_session
        )


# ================== ADMIN UPDATE PROFILE AND CONFIRM EMAIL TESTS ==================
@pytest.mark.asyncio
async def test_admin_update_profile_full_update(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)

    # Update all fields
    new_data = {
        "username": "newusername",
        "email": "newemail@example.com",
        "full_name": "New Name",
        "is_active": False
    }
    updated_user = await repository_users.admin_update_profile(
        user,
        username=new_data["username"],
        email=new_data["email"],
        full_name=new_data["full_name"],
        is_active=new_data["is_active"],
        db=db_session
    )

    # Verify all fields were updated
    assert updated_user.username == new_data["username"]
    assert updated_user.email == new_data["email"]
    assert updated_user.full_name == new_data["full_name"]
    assert updated_user.is_active == new_data["is_active"]
    # Verify other fields unchanged
    assert updated_user.password == user_data.password
    assert updated_user.is_admin == user.is_admin


@pytest.mark.asyncio
async def test_admin_update_profile_partial_update(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    original_email = user.email
    original_username = user.username
    original_is_active = user.is_active

    # Update only full_name
    new_full_name = "New Name"
    updated_user = await repository_users.admin_update_profile(
        user,
        full_name=new_full_name,
        db=db_session
    )

    # Verify only full_name was updated
    assert updated_user.full_name == new_full_name
    assert updated_user.email == original_email
    assert updated_user.username == original_username
    assert updated_user.is_active == original_is_active


@pytest.mark.asyncio
async def test_admin_update_profile_no_changes(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)
    original_state = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active
    }

    # Update with None values
    updated_user = await repository_users.admin_update_profile(
        user,
        username=None,
        email=None,
        full_name=None,
        is_active=None,
        db=db_session
    )

    # Verify no changes
    assert updated_user.username == original_state["username"]
    assert updated_user.email == original_state["email"]
    assert updated_user.full_name == original_state["full_name"]
    assert updated_user.is_active == original_state["is_active"]


@pytest.mark.asyncio
async def test_admin_confirm_email_success(
    db_session: AsyncSession,
    user_data
):
    # Create unconfirmed user
    user = await repository_users.create_user(user_data, db_session)
    assert not user.confirmed

    # Confirm email
    updated_user = await repository_users.admin_confirm_email(
        user,
        db_session
    )

    # Verify email was confirmed
    assert updated_user.confirmed
    # Verify in database
    db_user = await repository_users.get_user_by_email(
        user.email,
        db_session
    )
    assert db_user.confirmed


@pytest.mark.asyncio
async def test_admin_confirm_email_already_confirmed(
    db_session: AsyncSession,
    user_data
):
    # Create confirmed user
    user = await repository_users.create_user(user_data, db_session)
    await repository_users.admin_confirm_email(user, db_session)
    assert user.confirmed

    # Try to confirm again
    updated_user = await repository_users.admin_confirm_email(
        user,
        db_session
    )
    assert updated_user.confirmed


# ================== ADMIN UPDATE ADMIN STATUS AND DELETE USER TESTS ==================
@pytest.mark.asyncio
async def test_admin_update_admin_status_grant_admin(
    db_session: AsyncSession,
    user_data
):
    # Create regular user
    user = await repository_users.create_user(user_data, db_session)
    assert not user.is_admin

    # Grant admin status
    updated_user = await repository_users.admin_update_admin_status(
        user,
        is_admin=True,
        db=db_session
    )

    # Verify admin status was granted
    assert updated_user.is_admin
    # Verify in database
    db_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert db_user.is_admin


@pytest.mark.asyncio
async def test_admin_update_admin_status_revoke_admin(
    db_session: AsyncSession,
    user_data
):
    # Create admin user
    user = await repository_users.create_user(user_data, db_session)
    await repository_users.admin_update_admin_status(
        user,
        is_admin=True,
        db=db_session
    )
    assert user.is_admin

    # Revoke admin status
    updated_user = await repository_users.admin_update_admin_status(
        user,
        is_admin=False,
        db=db_session
    )

    # Verify admin status was revoked
    assert not updated_user.is_admin
    # Verify in database
    db_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert not db_user.is_admin


@pytest.mark.asyncio
async def test_delete_user_success(
    db_session: AsyncSession,
    user_data
):
    # Create user
    user = await repository_users.create_user(user_data, db_session)

    # Delete user
    await repository_users.delete_user(user, db_session)

    # Verify user was deleted
    deleted_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_user_cascade_refresh_token(
    db_session: AsyncSession,
    user_data
):
    # Create user with refresh token
    user = await repository_users.create_user(user_data, db_session)
    await repository_users.update_token(user, "test_token", db_session)
    assert user.refresh_token is not None

    # Delete user
    await repository_users.delete_user(user, db_session)

    # Verify user and token were deleted
    deleted_user = await repository_users.get_user_by_username(
        user.username,
        db_session
    )
    assert deleted_user is None