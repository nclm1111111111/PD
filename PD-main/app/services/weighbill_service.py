"""
磅单服务 - OCR识别 + 自动关联 + 手动修正
"""
import logging
import os
import re
import shutil
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

from PIL import Image, ImageEnhance, ImageFilter

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False

from app.core.paths import UPLOADS_DIR
from core.database import get_conn
from core.logging import get_logger

logger = get_logger(__name__)

UPLOAD_DIR = UPLOADS_DIR / "weighbills"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class WeighbillService:
    """磅单服务"""

    def __init__(self):
        self.ocr = None
        if RAPIDOCR_AVAILABLE:
            try:
                self.ocr = RapidOCR()
                logger.info("磅单OCR初始化成功")
            except Exception as e:
                logger.error(f"磅单OCR初始化失败: {e}")

    # ========== OCR相关方法 ==========

    def preprocess_image(self, image_path: str) -> str:
        """图片预处理"""
        try:
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 增强对比度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)

            # 锐化
            img = img.filter(ImageFilter.SHARPEN)

            # 调整大小
            max_size = 2000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 保存临时文件
            temp_path = tempfile.mktemp(suffix=".jpg")
            img.save(temp_path, "JPEG", quality=95)
            return temp_path

        except Exception as e:
            logger.error(f"预处理失败: {e}")
            return image_path

    def recognize_weighbill(self, image_path: str) -> Dict[str, Any]:
        """
        OCR识别磅单
        """
        if not self.ocr:
            return {
                "success": True,
                "data": self._empty_result("OCR未初始化"),
                "ocr_success": False
            }

        try:
            result, elapse = self.ocr(image_path)
            total_elapse = sum(elapse) if isinstance(elapse, list) else float(elapse or 0)

            if not result:
                return {
                    "success": True,
                    "data": self._empty_result("未能识别到文本"),
                    "ocr_success": False
                }

            # 提取文本行
            text_lines = []
            for item in result:
                bbox, text, confidence = item
                text_lines.append({"text": text.strip(), "confidence": float(confidence)})

            full_text = "\n".join([line["text"] for line in text_lines])

            logger.info("=== 磅单OCR识别文本 ===")
            for i, line in enumerate(text_lines):
                logger.info(f"{i}: {line['text']}")

            # 解析磅单
            data = self._parse_weighbill(text_lines, full_text)
            data["ocr_time"] = round(total_elapse, 3)
            data["raw_text"] = full_text

            return {
                "success": True,
                "data": data,
                "ocr_success": True
            }

        except Exception as e:
            logger.error(f"磅单识别异常: {e}")
            return {
                "success": True,
                "data": self._empty_result(f"识别异常: {str(e)}"),
                "ocr_success": False
            }

    def _empty_result(self, message: str) -> Dict:
        """返回空结果结构"""
        return {
            "weigh_date": None,
            "weigh_ticket_no": None,
            "contract_no": None,
            "vehicle_no": None,
            "product_name": None,
            "gross_weight": None,
            "tare_weight": None,
            "net_weight": None,
            "delivery_unit": None,
            "receive_unit": None,
            "ocr_message": message,
        }

    def _parse_weighbill(self, text_lines: List[Dict], full_text: str) -> Dict:
        """解析磅单信息"""
        # 提取各字段
        weigh_date = self._extract_date(full_text)
        ticket_no = self._extract_ticket_no(full_text)
        contract_no = self._extract_contract_no(full_text)
        vehicle_no = self._extract_vehicle_no(full_text)
        product_name = self._extract_product_name(full_text)
        gross, tare, net = self._extract_weights(full_text)
        delivery, receive = self._extract_units(full_text)

        # 检查缺失字段
        missing = []
        if not weigh_date:
            missing.append("日期")
        if not vehicle_no:
            missing.append("车牌号")
        if not net:
            missing.append("净重")
        if not contract_no:
            missing.append("合同编号")

        message = "识别完成"
        if missing:
            message = f"已识别，以下字段缺失需手动填写: {', '.join(missing)}"

        return {
            "weigh_date": weigh_date,
            "weigh_ticket_no": ticket_no,
            "contract_no": contract_no,
            "vehicle_no": vehicle_no,
            "product_name": product_name,
            "gross_weight": gross,
            "tare_weight": tare,
            "net_weight": net,
            "delivery_unit": delivery,
            "receive_unit": receive,
            "ocr_message": message,
        }

    def _extract_date(self, text: str) -> Optional[str]:
        """提取日期"""
        patterns = [
            r"日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            r"(\d{4}年\d{1,2}月\d{1,2}日)",
            r"(\d{4}-\d{1,2}-\d{1,2})",
            r"(\d{4}/\d{1,2}/\d{1,2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
                return date_str
        return None

    def _extract_ticket_no(self, text: str) -> Optional[str]:
        """提取过磅单号"""
        patterns = [
            r"单据号[：:]\s*(\d+)",
            r"磅单号[：:]\s*(\d+)",
            r"票号[：:]\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_contract_no(self, text: str) -> Optional[str]:
        """提取合同编号"""
        patterns = [
            r"合同编号[：:]\s*([A-Za-z0-9\-]+)",
            r"合同号[：:]\s*([A-Za-z0-9\-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_vehicle_no(self, text: str) -> Optional[str]:
        """提取车牌号"""
        patterns = [
            r"车号[：:]\s*([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6})",
            r"车牌[：:]\s*([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6})",
            r"([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,6})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_product_name(self, text: str) -> Optional[str]:
        """提取货物名称"""
        patterns = [
            r"货物名称[：:]\s*(.+?)(?:\n|$)",
            r"品名[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_weights(self, text: str) -> tuple:
        """提取重量"""
        gross = tare = net = None

        match = re.search(r"毛重[：:]\s*(\d+\.?\d*)", text)
        if match:
            gross = float(match.group(1))

        match = re.search(r"皮重[：:]\s*(\d+\.?\d*)", text)
        if match:
            tare = float(match.group(1))

        match = re.search(r"净重[：:]\s*(\d+\.?\d*)", text)
        if match:
            net = float(match.group(1))

        return gross, tare, net

    def _extract_units(self, text: str) -> tuple:
        """提取送货/收货单位"""
        delivery = receive = None

        match = re.search(r"送货单位[：:]\s*(.+?)(?:\n|$)", text)
        if match:
            delivery = match.group(1).strip()

        match = re.search(r"收货单位[：:]\s*(.+?)(?:\n|$)", text)
        if match:
            receive = match.group(1).strip()

        return delivery, receive

    # ========== 自动关联方法 ==========

    def match_delivery_info(self, weigh_date: str, vehicle_no: str) -> Optional[Dict]:
        """
        通过日期+车牌号匹配报货订单
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM pd_deliveries 
                        WHERE vehicle_no = %s 
                        AND (
                            report_date = %s 
                            OR report_date = DATE_ADD(%s, INTERVAL 1 DAY)
                            OR report_date = DATE_SUB(%s, INTERVAL 1 DAY)
                        )
                        AND status != '已取消'
                        ORDER BY ABS(DATEDIFF(report_date, %s)), created_at DESC
                        LIMIT 1
                    """, (vehicle_no, weigh_date, weigh_date, weigh_date, weigh_date))

                    row = cur.fetchone()
                    if not row:
                        return None

                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))

        except Exception as e:
            logger.error(f"匹配报货订单失败: {e}")
            return None

    def get_contract_price(self, contract_no: str, product_name: str) -> Optional[float]:
        """
        根据合同编号和品种获取单价
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # 品种映射表
                    product_mapping = {
                        "废电瓶": ["电动车", "新能源", "通信", "摩托车", "大白", "牵引", "黑皮"],
                        "新能源电瓶": ["新能源"],
                        "电动车电瓶": ["电动车"],
                    }

                    cur.execute("""
                        SELECT p.product_name, p.unit_price 
                        FROM pd_contract_products p
                        JOIN pd_contracts c ON p.contract_id = c.id
                        WHERE c.contract_no = %s 
                        AND p.unit_price IS NOT NULL
                        AND p.unit_price > 0
                        ORDER BY p.sort_order
                    """, (contract_no,))

                    products = {}
                    for row in cur.fetchall():
                        if row[1]:
                            products[row[0]] = float(row[1])

                    if not products:
                        return None

                    # 直接匹配
                    if product_name in products:
                        return products[product_name]

                    # 通过映射匹配
                    for key, mapped_products in product_mapping.items():
                        if key in product_name:
                            for mp in mapped_products:
                                if mp in products:
                                    return products[mp]

                    # 返回第一个有价格的品种
                    return list(products.values())[0]

        except Exception as e:
            logger.error(f"获取合同价格失败: {e}")
            return None

    def auto_fill_data(self, ocr_data: Dict) -> Dict:
        """
        自动关联填充数据
        """
        result = ocr_data.copy()

        weigh_date = ocr_data.get("weigh_date")
        vehicle_no = ocr_data.get("vehicle_no")
        contract_no = ocr_data.get("contract_no")
        product_name = ocr_data.get("product_name")
        net_weight = ocr_data.get("net_weight")

        # 1. 匹配报货订单
        if weigh_date and vehicle_no:
            delivery = self.match_delivery_info(weigh_date, vehicle_no)
            if delivery:
                result["matched_delivery_id"] = delivery["id"]
                result["warehouse"] = delivery.get("warehouse")
                result["target_factory_name"] = delivery.get("target_factory_name")
                result["driver_name"] = delivery.get("driver_name")
                result["driver_phone"] = delivery.get("driver_phone")
                result["driver_id_card"] = delivery.get("driver_id_card")
                result["match_message"] = "已匹配报货订单"
            else:
                result["match_message"] = "未找到匹配的报货订单，请手动填写"

        # 2. 获取合同单价
        if contract_no and product_name:
            price = self.get_contract_price(contract_no, product_name)
            if price:
                result["unit_price"] = price
                if net_weight:
                    result["total_amount"] = round(price * net_weight, 2)
                result["price_message"] = f"已获取合同单价（品种：{product_name}）"
            else:
                result["price_message"] = "未找到合同单价，请手动填写"
        elif contract_no:
            price = self.get_contract_price(contract_no, "废电瓶")
            if price:
                result["unit_price"] = price
                if net_weight:
                    result["total_amount"] = round(price * net_weight, 2)
                result["price_message"] = "已获取合同默认单价"
            else:
                result["price_message"] = "未找到合同单价，请手动填写"

        return result

    # ========== 数据库操作方法 ==========

    def create_weighbill(
        self,
        data: Dict,
        image_path: str = None,
        is_manual: bool = False,
        current_user: dict = None
    ) -> Dict[str, Any]:
        """
        创建磅单记录
        """
        try:
            # 处理操作人信息
            uploader_id = None
            uploader_name = "system"
            if current_user:
                uploader_id = current_user.get("id")
                uploader_name = current_user.get("name") or current_user.get("account") or "system"

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO pd_weighbills 
                        (weigh_date, delivery_time, weigh_ticket_no, contract_no, delivery_id, vehicle_no,
                         product_name, gross_weight, tare_weight, net_weight,
                         unit_price, total_amount, weighbill_image, ocr_status, 
                         ocr_raw_data, is_manual_corrected, uploader_id, uploader_name, uploaded_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        data.get("weigh_date"),
                        data.get("delivery_time"),
                        data.get("weigh_ticket_no"),
                        data.get("contract_no"),
                        data.get("matched_delivery_id"),
                        data.get("vehicle_no"),
                        data.get("product_name"),
                        data.get("gross_weight"),
                        data.get("tare_weight"),
                        data.get("net_weight"),
                        data.get("unit_price"),
                        data.get("total_amount"),
                        image_path,
                        "已确认" if is_manual else "待确认",
                        data.get("raw_text"),
                        1 if is_manual else 0,
                        uploader_id,
                        uploader_name,
                    ))

                    bill_id = cur.lastrowid
                    conn.commit()

                    return {
                        "success": True,
                        "message": "磅单保存成功",
                        "data": {
                            "id": bill_id,
                            "uploader_id": uploader_id,
                            "uploader_name": uploader_name,
                        }
                    }

        except Exception as e:
            logger.error(f"保存磅单失败: {e}")
            return {"success": False, "error": str(e)}

    def get_weighbill(self, bill_id: int) -> Optional[Dict]:
        """
        获取磅单详情
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT w.*, d.shipper, d.payee
                        FROM pd_weighbills w
                        LEFT JOIN pd_deliveries d ON w.delivery_id = d.id
                        WHERE w.id = %s
                    """, (bill_id,))

                    row = cur.fetchone()
                    if not row:
                        return None

                    columns = [desc[0] for desc in cur.description]
                    data = dict(zip(columns, row))

                    # 转换时间
                    for key in ["weigh_date", "delivery_time", "created_at", "updated_at", "uploaded_at"]:
                        if data.get(key):
                            data[key] = str(data[key])

                    return data

        except Exception as e:
            logger.error(f"查询磅单失败: {e}")
            return None

    def list_weighbills(
        self,
        exact_status: Optional[str] = None,
        exact_vehicle_no: Optional[str] = None,
        exact_contract_no: Optional[str] = None,
        fuzzy_keywords: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        查询磅单列表
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    where_clauses = ["1=1"]
                    params = []

                    if exact_status:
                        where_clauses.append("w.ocr_status = %s")
                        params.append(exact_status)

                    if exact_vehicle_no:
                        where_clauses.append("w.vehicle_no = %s")
                        params.append(exact_vehicle_no)

                    if exact_contract_no:
                        where_clauses.append("w.contract_no = %s")
                        params.append(exact_contract_no)

                    if date_from:
                        where_clauses.append("w.weigh_date >= %s")
                        params.append(date_from)

                    if date_to:
                        where_clauses.append("w.weigh_date <= %s")
                        params.append(date_to)

                    if fuzzy_keywords:
                        tokens = [t for t in fuzzy_keywords.split() if t]
                        or_clauses = []
                        for token in tokens:
                            like = f"%{token}%"
                            or_clauses.append(
                                "(w.contract_no LIKE %s OR w.vehicle_no LIKE %s OR w.product_name LIKE %s "
                                "OR w.weigh_ticket_no LIKE %s)"
                            )
                            params.extend([like, like, like, like])
                        if or_clauses:
                            where_clauses.append("(" + " OR ".join(or_clauses) + ")")

                    where = "WHERE " + " AND ".join(where_clauses)

                    # 总数
                    cur.execute(f"SELECT COUNT(*) FROM pd_weighbills w {where}", tuple(params))
                    total = cur.fetchone()["COUNT(*)"]

                    # 分页
                    offset = (page - 1) * page_size
                    cur.execute(f"""
                        SELECT
                            w.*,
                            d.warehouse,
                            d.target_factory_name,
                            d.driver_name,
                            d.driver_phone,
                            d.driver_id_card,
                            d.shipper,
                            d.payee
                        FROM pd_weighbills w
                        LEFT JOIN pd_deliveries d ON w.delivery_id = d.id
                        {where}
                        ORDER BY w.created_at DESC
                        LIMIT %s OFFSET %s
                    """, tuple(params + [page_size, offset]))

                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    data = []
                    for row in rows:
                        item = dict(zip(columns, row))
                        for key in ["weigh_date", "delivery_time", "created_at", "updated_at", "uploaded_at"]:
                            if item.get(key):
                                item[key] = str(item[key])
                        data.append(item)

                    return {
                        "success": True,
                        "data": data,
                        "total": total,
                        "page": page,
                        "page_size": page_size
                    }

        except Exception as e:
            logger.error(f"查询磅单列表失败: {e}")
            return {"success": False, "error": str(e), "data": [], "total": 0}

    def confirm_weighbill(self, bill_id: int) -> Dict[str, Any]:
        """
        确认磅单
        """
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # 获取磅单信息
                    cur.execute(
                        "SELECT delivery_id FROM pd_weighbills WHERE id = %s",
                        (bill_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return {"success": False, "error": "磅单不存在"}

                    delivery_id = row["delivery_id"]

                    # 更新磅单状态
                    cur.execute(
                        "UPDATE pd_weighbills SET ocr_status = '已确认' WHERE id = %s",
                        (bill_id,)
                    )

                    # 更新关联的报货订单状态
                    if delivery_id:
                        cur.execute("""
                            UPDATE pd_deliveries
                            SET status = '已完成'
                            WHERE id = %s AND status NOT IN ('已取消', '已完成')
                        """, (delivery_id,))

                    conn.commit()

                    return {
                        "success": True,
                        "message": "磅单已确认",
                        "data": {
                            "weighbill_id": bill_id,
                            "delivery_id": delivery_id
                        }
                    }

        except Exception as e:
            logger.error(f"确认磅单失败: {e}")
            return {"success": False, "error": str(e)}


# 单例模式
_weighbill_service = None


def get_weighbill_service():
    """获取磅单服务实例"""
    global _weighbill_service
    if _weighbill_service is None:
        _weighbill_service = WeighbillService()
    return _weighbill_service