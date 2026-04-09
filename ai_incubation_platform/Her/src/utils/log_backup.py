"""
日志备份工具
系统重启时自动备份日志文件到归档目录
"""
import os
import shutil
from typing import Optional
from datetime import datetime

from config import settings
from utils.logger import logger


class LogBackup:
    """日志备份器"""

    def __init__(
        self,
        log_dir: Optional[str] = None,
        backup_dir: Optional[str] = None,
        enabled: bool = True,
        keep_backups: int = 10
    ):
        """
        初始化日志备份器

        Args:
            log_dir: 日志目录路径，默认使用项目 logs 目录
            backup_dir: 备份目录路径，默认在 logs/archive 子目录
            enabled: 是否启用备份功能
            keep_backups: 保留的备份数量，超过此数量时删除最旧的备份
        """
        if log_dir is None:
            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'logs'
            )
        if backup_dir is None:
            backup_dir = os.path.join(log_dir, 'archive')

        self.log_dir = log_dir
        self.backup_dir = backup_dir
        self.enabled = enabled
        self.keep_backups = keep_backups

    def backup_on_startup(self) -> dict:
        """
        系统启动时备份日志

        Returns:
            备份结果统计信息
        """
        if not self.enabled:
            logger.info("Log backup is disabled, skipping backup")
            return {"status": "disabled"}

        logger.info(f"Starting log backup from {self.log_dir} to {self.backup_dir}")

        result = {
            "status": "success",
            "backed_up_files": 0,
            "total_size_mb": 0.0,
            "deleted_old_backups": 0,
            "backup_timestamp": datetime.now().isoformat(),
            "errors": []
        }

        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)

        # 获取需要备份的日志文件
        try:
            log_files = self._get_log_files()
        except Exception as e:
            logger.error(f"Failed to get log files: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))
            return result

        if not log_files:
            logger.info("No log files to backup")
            return result

        # 生成备份时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 备份每个日志文件
        for file_info in log_files:
            try:
                backup_path = self._backup_file(file_info, timestamp)
                if backup_path:
                    result["backed_up_files"] += 1
                    result["total_size_mb"] += file_info["size"] / (1024 * 1024)
                    logger.info(f"Backed up log file: {file_info['name']} -> {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup {file_info['name']}: {e}")
                result["errors"].append(f"Failed to backup {file_info['name']}: {e}")

        # 清理旧备份
        deleted_count = self._cleanup_old_backups()
        result["deleted_old_backups"] = deleted_count

        logger.info(
            f"Log backup completed: "
            f"backed_up={result['backed_up_files']} files, "
            f"total_size={result['total_size_mb']:.2f}MB, "
            f"deleted_old_backups={result['deleted_old_backups']}"
        )

        return result

    def _get_log_files(self) -> list:
        """获取日志目录中需要备份的日志文件"""
        log_files = []
        for filename in os.listdir(self.log_dir):
            filepath = os.path.join(self.log_dir, filename)
            # 只备份 .log 文件，跳过已经是归档的文件
            if os.path.isfile(filepath) and filename.endswith('.log'):
                size = os.path.getsize(filepath)
                # 只备份非空文件
                if size > 0:
                    log_files.append({
                        "path": filepath,
                        "name": filename,
                        "size": size,
                        "mtime": os.path.getmtime(filepath)
                    })
        return log_files

    def _backup_file(self, file_info: dict, timestamp: str) -> Optional[str]:
        """
        备份单个日志文件，备份后清空原文件

        Args:
            file_info: 文件信息字典
            timestamp: 时间戳字符串

        Returns:
            备份文件路径，如果失败返回 None
        """
        # 生成备份文件名：server.log -> server_20260409_143022.log
        name_parts = file_info["name"].rsplit('.', 1)
        if len(name_parts) == 2:
            backup_filename = f"{name_parts[0]}_{timestamp}.log"
        else:
            backup_filename = f"{file_info['name']}_{timestamp}"

        backup_path = os.path.join(self.backup_dir, backup_filename)

        # 复制文件
        shutil.copy2(file_info["path"], backup_path)

        # 清空原日志文件（保留文件以便继续写入）
        with open(file_info["path"], 'w', encoding='utf-8') as f:
            f.write('')  # 清空文件内容

        logger.info(f"Cleared log file: {file_info['name']}")

        return backup_path

    def _cleanup_old_backups(self) -> int:
        """
        清理旧的备份文件，保留最近的 keep_backups 个

        Returns:
            删除的备份数量
        """
        deleted = 0

        # 获取所有备份文件
        backup_files = []
        for filename in os.listdir(self.backup_dir):
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.log'):
                backup_files.append({
                    "path": filepath,
                    "name": filename,
                    "mtime": os.path.getmtime(filepath)
                })

        # 如果备份数量未超过限制，不删除
        if len(backup_files) <= self.keep_backups:
            return deleted

        # 按修改时间排序，删除最旧的
        sorted_files = sorted(backup_files, key=lambda x: x["mtime"])
        files_to_delete = sorted_files[:len(backup_files) - self.keep_backups]

        for file_info in files_to_delete:
            try:
                os.remove(file_info["path"])
                deleted += 1
                logger.info(f"Deleted old backup: {file_info['name']}")
            except Exception as e:
                logger.error(f"Failed to delete backup {file_info['name']}: {e}")

        return deleted


# 全局备份器实例
log_backup = LogBackup(
    keep_backups=settings.log_backup_keep_count  # 保留最近 N 次重启的日志备份
)


def backup_logs_on_startup() -> dict:
    """
    系统启动时备份日志
    在 main.py 的 startup_event 中调用
    """
    logger.info("Running startup log backup...")
    return log_backup.backup_on_startup()
