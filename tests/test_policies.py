from data_engineering_exports.policies import create_pull_bucket_policy, create_read_write_role_policy

def test_create_pull_bucket_policy():
    assert not create_pull_bucket_policy()


def test_create_read_write_role_policy():
    assert not create_read_write_role_policy()
