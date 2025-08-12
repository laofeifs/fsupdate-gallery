# 超特角色排名调查系统

一个用于收集玩家对超特角色排名的调查系统。

## 功能特性

- 📊 六个职业的独立排名（C, PF, PG, SG, SF, SW）
- 🎯 每个角色可参与多个职业排名
- 📱 移动端友好的界面
- 🔒 防止重复投票
- 📈 实时统计和结果查看

## 部署方法

### 方法一：Vercel 部署（推荐）

1. Fork 这个仓库到你的 GitHub
2. 在 Vercel 中导入项目
3. 自动部署完成

### 方法二：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务器
python3 survey_app.py
```

## 访问地址

- 调查页面：`/survey`
- 管理后台：`/survey/results`

## 技术栈

- 后端：Flask + SQLite
- 前端：HTML + CSS + JavaScript
- 部署：Vercel
