# pattern: Functional Core tests
# Tests for permission checking functions

import os
from talk_it_out.framework import permissions


def test_get_user_groups_returns_list():
    """get_user_groups should return list of group names"""
    groups = permissions.get_user_groups()

    assert isinstance(groups, list)
    assert len(groups) > 0
    assert all(isinstance(g, str) for g in groups)


def test_get_user_groups_includes_current_user_group():
    """User's primary group should be in the list"""
    groups = permissions.get_user_groups()

    # User should at least be in their own group
    import grp
    primary_gid = os.getgid()
    primary_group = grp.getgrgid(primary_gid).gr_name

    assert primary_group in groups


def test_check_input_group_returns_tuple():
    """check_input_group should return (bool, str) tuple"""
    result = permissions.check_input_group()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)


def test_check_input_group_error_message_has_instructions():
    """If not in input group, error should have instructions"""
    success, error = permissions.check_input_group()

    if not success:
        # Error message should contain helpful instructions
        assert "input" in error.lower()
        assert "usermod" in error.lower() or "group" in error.lower()
