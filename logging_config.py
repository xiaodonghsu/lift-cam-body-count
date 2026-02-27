import logging
import os

def setup_logger(log_file='app.log', log_level=logging.INFO):
    # 创建日志目录（如果不存在）
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件路径
    log_file_path = os.path.join(log_dir, log_file)
    
    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(log_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建日志格式
    formatter = logging.Formatter('[%(asctime)s] %(filename)s->%(funcName)s line:%(lineno)d [%(levelname)s]%(message)s')
    
    # 将格式应用到处理器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
