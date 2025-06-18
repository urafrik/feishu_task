import os

def pytest_configure(config):
    """
    在 pytest 测试收集阶段开始前执行，用于设置全局配置。
    我们在这里设置环境变量，以确保 pydantic Settings 在模块导入时
    就能成功加载，解决测试收集阶段的 ValidationError。
    """
    # 模拟飞书配置
    os.environ.setdefault('FEISHU__APP_ID', 'test_app_id')
    os.environ.setdefault('FEISHU__APP_SECRET', 'test_app_secret')
    os.environ.setdefault('FEISHU__VERIFICATION_TOKEN', 'test_verification_token')
    os.environ.setdefault('FEISHU__ENCRYPT_KEY', 'test_encrypt_key')
    
    # 模拟多维表配置
    os.environ.setdefault('BITABLE__APP_TOKEN', 'test_app_token')
    os.environ.setdefault('BITABLE__TASK_TABLE_ID', 'test_task_table_id')
    os.environ.setdefault('BITABLE__PERSON_TABLE_ID', 'test_person_table_id')
    
    # 模拟 LLM 配置
    os.environ.setdefault('LLM__DEFAULT_PROVIDER', 'openai')
    os.environ.setdefault('LLM__PROVIDERS__OPENAI__MODEL', 'gpt-4')
    os.environ.setdefault('LLM__PROVIDERS__OPENAI__API_KEY', 'fake_key')
    
    # 启用 CI/GitHub Webhook 功能
    os.environ['CI__ENABLED'] = 'true'
    os.environ['CI__WEBHOOK_SECRET'] = 'test_github_secret' 