import asyncio

from openbalancer.router import ArtificialProviderLimiter


def test_artificial_limiter_rejects_above_concurrency_limit():
    async def scenario():
        limiter = ArtificialProviderLimiter(max_concurrent=2)

        first, first_reason, first_retry_after = await limiter.try_acquire()
        second, second_reason, second_retry_after = await limiter.try_acquire()
        third, third_reason, third_retry_after = await limiter.try_acquire()

        assert first is True
        assert first_reason is None
        assert first_retry_after == 0
        assert second is True
        assert second_reason is None
        assert second_retry_after == 0
        assert third is False
        assert "concurrency limit" in third_reason
        assert third_retry_after > 0

        await limiter.release()
        after_release, after_release_reason, after_release_retry_after = await limiter.try_acquire()

        assert after_release is True
        assert after_release_reason is None
        assert after_release_retry_after == 0

    asyncio.run(scenario())
