import os
import pytest
import openai
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.utils.logger import get_logger

logger = get_logger("live_test")

# This test only runs if CT_LIVE_API_URL is set
@pytest.mark.skipif(not os.environ.get("CT_LIVE_API_URL"), reason="CT_LIVE_API_URL not set")
def test_live_model_connectivity():
    """
    Verifies that the toolkit can connect to a real/local LLM endpoint
    and perform a basic chat + divergence scoring flow.
    """
    API_URL = os.environ.get("CT_LIVE_API_URL")
    LLM_MODEL = os.environ.get("CT_LIVE_LLM_MODEL", "qwen/qwen3-coder-30b")
    EMB_MODEL = os.environ.get("CT_LIVE_EMB_MODEL", "text-embedding-qwen3-embedding-0.6b")
    
    # Initialize client
    client = openai.OpenAI(
        base_url=f"{API_URL}/v1",
        api_key=os.environ.get("OPENAI_API_KEY", "dummy")
    )
    
    # 1. Initialize Wrapper
    config = WrapperConfig(
        template="general",
        embedding_client=client,
        embedding_model=EMB_MODEL,
        divergence_l1_threshold=0.1,
        log_requests=True,
    )
    
    wrapper = TheseusWrapper(client, config)
    
    # 2. Test Chat
    try:
        response = wrapper.chat(
            "Hello! This is a structural connectivity test. State your purpose briefly.",
            model=LLM_MODEL
        )
        
        assert response.content is not None
        assert len(response.content) > 0
        assert response.divergence_score is not None
        assert 0.0 <= response.divergence_score <= 1.0
        
        logger.info(f"Live Test Result: Score={response.divergence_score}, Tier={response.divergence_tier}")
        
    except Exception as e:
        pytest.fail(f"Live model connectivity test failed: {e}")
