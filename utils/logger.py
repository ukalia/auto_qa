import logging
import inspect
from functools import wraps
import time

class Logger:

    def __init__(self, name=None):
        if not name:
            frame = inspect.currentframe().f_back
            self.name = frame.f_globals.get('__name__', 'auto_qa')
        else:
            self.name = name
        self.logger = logging.getLogger(self.name)

    @classmethod
    def setup_logging(cls):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    @staticmethod
    def log_function_call(logger=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not logger:
                    func_logger = Logger(func.__module__).logger
                else:
                    func_logger = logger
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                
                func_logger.debug(f"Calling {func.__name__}({signature})")
                
                try:
                    result = func(*args, **kwargs)
                    func_logger.debug(f"{func.__name__} completed successfully")
                    return result
                except Exception as e:
                    func_logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                    raise
            return wrapper
        return decorator

    @staticmethod
    def log_execution_time(logger=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):                
                if logger is None:
                    func_logger = Logger().get_logger
                else:
                    func_logger = logger
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    func_logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    func_logger.error(f"{func.__name__} failed after {execution_time:.4f} seconds: {str(e)}")
                    raise
            return wrapper
        return decorator  
    
    