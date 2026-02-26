"""
文件处理工具函数
用于文件上传、保存、删除等操作
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
import re

from fastapi import UploadFile
from core.logging import get_logger

logger = get_logger(__name__)

# 允许的文件类型
ALLOWED_IMAGES = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
ALLOWED_DOCUMENTS = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}
ALLOWED_ALL = ALLOWED_IMAGES | ALLOWED_DOCUMENTS


def ensure_dir_exists(dir_path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写，不含点）
    """
    if '.' not in filename:
        return ''
    return filename.split('.')[-1].lower()


def is_allowed_extension(
        filename: str,
        allowed_extensions: set = ALLOWED_ALL
) -> bool:
    """
    检查文件扩展名是否允许
    """
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）
    """
    path = Path(file_path)
    if path.exists() and path.is_file():
        return path.stat().st_size
    return 0


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def generate_filename(original_filename: str, prefix: str = "") -> str:
    """
    生成唯一文件名
    格式: [prefix_]年月日_时分秒_uuid8.扩展名
    """
    ext = get_file_extension(original_filename)

    # 清理原始文件名中的特殊字符
    base_name = os.path.splitext(original_filename)[0]
    base_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', base_name)

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 生成随机字符串
    random_str = str(uuid.uuid4())[:8]

    if prefix:
        filename = f"{prefix}_{timestamp}_{random_str}"
    else:
        filename = f"{timestamp}_{random_str}"

    if ext:
        filename += f".{ext}"

    return filename


async def save_upload_file(
        file: UploadFile,
        upload_dir: Union[str, Path],
        filename: Optional[str] = None,
        max_size: int = 10 * 1024 * 1024  # 默认10MB
) -> Optional[Path]:
    """
    保存上传的文件
    返回保存后的文件路径，失败返回None
    """
    try:
        # 确保上传目录存在
        upload_path = ensure_dir_exists(upload_dir)

        # 生成文件名
        if not filename:
            filename = generate_filename(file.filename)
        elif not filename.endswith(get_file_extension(file.filename)):
            # 如果指定的文件名没有扩展名，添加原始扩展名
            ext = get_file_extension(file.filename)
            if ext:
                filename = f"{filename}.{ext}"

        file_path = upload_path / filename

        # 保存文件
        file_size = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 每次读取1MB
                file_size += len(chunk)
                if file_size > max_size:
                    buffer.close()
                    os.remove(file_path)
                    logger.error(f"文件过大: {file_size} > {max_size}")
                    return None
                buffer.write(chunk)

        logger.info(f"文件保存成功: {file_path} ({format_file_size(file_size)})")
        return file_path

    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        return None


def delete_file(file_path: Union[str, Path]) -> bool:
    """
    删除文件
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            os.remove(path)
            logger.info(f"文件删除成功: {file_path}")
            return True
    except Exception as e:
        logger.error(f"删除文件失败: {file_path}, 错误: {e}")

    return False


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """
    移动文件
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        # 确保目标目录存在
        ensure_dir_exists(dst_path.parent)

        shutil.move(str(src_path), str(dst_path))
        logger.info(f"文件移动成功: {src} -> {dst}")
        return True

    except Exception as e:
        logger.error(f"移动文件失败: {e}")
        return False


def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """
    复制文件
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        ensure_dir_exists(dst_path.parent)

        shutil.copy2(str(src_path), str(dst_path))
        logger.info(f"文件复制成功: {src} -> {dst}")
        return True

    except Exception as e:
        logger.error(f"复制文件失败: {e}")
        return False


def get_file_info(file_path: Union[str, Path]) -> dict:
    """
    获取文件信息
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return {}

    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "extension": get_file_extension(path.name),
        "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_file": True
    }


def clean_temp_files(temp_dir: Union[str, Path], max_age_hours: int = 24):
    """
    清理临时文件
    删除超过指定时间的文件
    """
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return

    now = datetime.now()
    deleted_count = 0

    for file_path in temp_path.glob("*"):
        if file_path.is_file():
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            age = now - modified_time

            if age.total_seconds() > max_age_hours * 3600:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"清理临时文件失败: {file_path}, {e}")

    if deleted_count > 0:
        logger.info(f"清理了 {deleted_count} 个临时文件")