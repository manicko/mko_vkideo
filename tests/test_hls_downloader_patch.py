async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
            nonlocal gather_called
            gather_called = True
            # Return True for each task
            return [True] * len(tasks)