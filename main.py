import streamlit as st
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date

# ---------- 第1部分：加载环境变量并连接数据库 ----------
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    st.error("❌ 请检查 .env 文件，确保 SUPABASE_URL 和 SUPABASE_KEY 已正确设置")
    st.stop()

supabase = create_client(url, key)

# ---------- 第2部分：页面标题 ----------
st.set_page_config(page_title="淑女坊记账系统", layout="wide")
st.title("👗 淑女坊记账系统")

# ---------- 第3部分：侧边栏菜单 ----------
menu = st.sidebar.selectbox("选择功能", ["📝 录入订单", "📊 今日对账", "📋 历史订单", "🖨️ 打印面单"])

# ---------- 功能1：录入订单 ----------
if menu == "📝 录入订单":
    st.header("录入新订单")
    
    with st.form("order_form"):
        col1, col2 = st.columns(2)
        with col1:
            customer = st.text_input("客户名称", placeholder="例如：张三批发")
            model = st.text_input("衣物型号", placeholder="例如：T-001")
            quantity = st.number_input("件数", min_value=1, step=1)
        with col2:
            price = st.number_input("单价（元）", min_value=0.0, step=1.0, format="%.2f")
            paid = st.number_input("已收款（元）", min_value=0.0, step=1.0, format="%.2f")
            address = st.text_area("收货地址（用于打印面单）", placeholder="省市区详细地址")
        
        # 新增：快递公司选择
        express_company = st.selectbox("快递公司", ["顺丰", "中通", "圆通", "韵达", "申通", "极兔", "EMS", "其他"])
        
        submitted = st.form_submit_button("✅ 保存订单")
        
        if submitted:
            if not customer or not model:
                st.warning("请填写客户名称和衣物型号")
            else:
                total = quantity * price
                # 自动生成运单号：快递公司缩写 + 日期 + 随机数
                import random
                express_code = {
                    "顺丰": "SF", "中通": "ZT", "圆通": "YT", 
                    "韵达": "YD", "申通": "ST", "极兔": "JT", 
                    "EMS": "EMS", "其他": "QT"
                }
                tracking_number = f"{express_code.get(express_company, 'SF')}{date.today().strftime('%Y%m%d')}{random.randint(100, 999)}"
                
                data = {
                    "customer_name": customer,
                    "model": model,
                    "quantity": quantity,
                    "price": price,
                    "total_price": total,
                    "paid_amount": paid,
                    "address": address,
                    "tracking_number": tracking_number,
                    "express_company": express_company  # 新增字段
                }
                try:
                    result = supabase.table("orders").insert(data).execute()
                    st.success(f"✅ 订单保存成功！应收：¥{total:.2f}，已收：¥{paid:.2f}，运单号：{tracking_number}")
                except Exception as e:
                    st.error(f"❌ 保存失败：{e}")

# ---------- 功能2：今日对账 ----------
elif menu == "📊 今日对账":
    st.header(f"📊 对账 - {date.today()}")
    
    try:
        response = supabase.table("orders").select("*").gte("created_at", str(date.today())).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.info("今天还没有订单")
        else:
            total_sales = df["total_price"].sum()
            total_paid = df["paid_amount"].sum()
            diff = total_paid - total_sales
            
            col1, col2, col3 = st.columns(3)
            col1.metric("总销售额", f"¥{total_sales:.2f}")
            col2.metric("已收款", f"¥{total_paid:.2f}")
            color = "inverse" if diff < 0 else "normal"
            col3.metric("差额", f"¥{diff:.2f}", delta=diff, delta_color=color)
            
            st.subheader("今日订单明细")
            # 重命名列为中文
            rename_map = {
                "customer_name": "客户名称",
                "model": "衣物型号",
                "quantity": "件数",
                "total_price": "总价",
                "paid_amount": "已收款",
                "express_company": "快递公司",
                "tracking_number": "运单号"
            }
            display_df = df.rename(columns=rename_map)
            # 只显示需要的列
            display_cols = ["客户名称", "衣物型号", "件数", "总价", "已收款", "快递公司", "运单号"]
            display_df = display_df[[col for col in display_cols if col in display_df.columns]]
            st.dataframe(display_df)
            
            if st.button("📌 保存今日对账记录"):
                check_data = {
                    "check_date": str(date.today()),
                    "total_sales": float(total_sales),
                    "total_received": float(total_paid),
                    "difference": float(diff),
                    "status": "正常" if diff == 0 else ("多收" if diff > 0 else "少收")
                }
                supabase.table("daily_check").insert(check_data).execute()
                st.success("对账记录已保存")
    except Exception as e:
        st.error(f"加载数据失败：{e}")

# ---------- 功能3：历史订单 ----------
elif menu == "📋 历史订单":
    st.header("历史订单查询")
    
    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).limit(100).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            # 重命名列为中文
            rename_map = {
                "created_at": "创建时间",
                "customer_name": "客户名称",
                "model": "衣物型号",
                "quantity": "件数",
                "total_price": "总价",
                "paid_amount": "已收款",
                "address": "收货地址",
                "express_company": "快递公司",
                "tracking_number": "运单号"
            }
            display_df = df.rename(columns=rename_map)
            display_cols = ["创建时间", "客户名称", "衣物型号", "件数", "总价", "已收款", "快递公司", "运单号", "收货地址"]
            display_df = display_df[[col for col in display_cols if col in display_df.columns]]
            st.dataframe(display_df)
        else:
            st.info("暂无历史订单")
    except Exception as e:
        st.error(f"加载失败：{e}")

# ---------- 功能4：打印面单 ----------
elif menu == "🖨️ 打印面单":
    st.header("生成快递面单")
    
    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).limit(20).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.info("暂无订单")
        else:
            selected = st.selectbox("选择订单", df["id"].tolist(), format_func=lambda x: f"订单 #{x} - {df[df['id']==x]['customer_name'].iloc[0]}")
            
            if selected:
                order = df[df["id"] == selected].iloc[0]
                express = order.get('express_company', '顺丰')
                html = f"""
                <div style="border:2px solid #333;padding:20px;width:350px;margin:auto;font-family:sans-serif;">
                    <h3 style="text-align:center;color:#d42e2e;">👗 淑女坊</h3>
                    <hr>
                    <p><strong>收件人：</strong>{order['customer_name']}</p>
                    <p><strong>地址：</strong>{order.get('address', '未填写')}</p>
                    <p><strong>快递：</strong>{express}</p>
                    <p><strong>运单号：</strong>{order.get('tracking_number', '未生成')}</p>
                    <p><strong>件数：</strong>{order['quantity']} 件</p>
                    <hr>
                    <p style="text-align:center;color:#888;font-size:12px;">生成时间：{date.today()}</p>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 下载面单（HTML格式，右键可打印）",
                    data=html,
                    file_name=f"面单_{order['customer_name']}_{date.today()}.html",
                    mime="text/html"
                )
    except Exception as e:
        st.error(f"加载失败：{e}")

# ---------- 底部提示 ----------
st.sidebar.markdown("---")
st.sidebar.caption("💡 数据存储在 Supabase 云端，永不丢失")