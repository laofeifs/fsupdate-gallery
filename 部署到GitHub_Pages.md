# 🚀 部署到GitHub Pages指南

## 📋 步骤概览

1. 创建GitHub仓库
2. 推送代码到GitHub
3. 启用GitHub Pages
4. 获取访问链接

## 🔧 详细步骤

### 第一步：创建GitHub仓库

1. 打开浏览器，访问 [GitHub.com](https://github.com)
2. 登录您的GitHub账户
3. 点击右上角的 "+" 号，选择 "New repository"
4. 填写仓库信息：
   - **Repository name**: `fsupdate-gallery` (或您喜欢的名称)
   - **Description**: `街头篮球7月31日更新文件图片集`
   - **Visibility**: 选择 `Public` (公开)
   - **不要**勾选 "Add a README file"
   - **不要**勾选 "Add .gitignore"
   - **不要**勾选 "Choose a license"
5. 点击 "Create repository"

### 第二步：推送代码到GitHub

在终端中执行以下命令（替换 `YOUR_USERNAME` 为您的GitHub用户名）：

```bash
# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/fsupdate-gallery.git

# 推送代码到GitHub
git branch -M main
git push -u origin main
```

### 第三步：启用GitHub Pages

1. 在GitHub仓库页面，点击 "Settings" 标签
2. 在左侧菜单中找到 "Pages"
3. 在 "Source" 部分：
   - 选择 "Deploy from a branch"
   - Branch 选择 "main"
   - Folder 选择 "/ (root)"
4. 点击 "Save"

### 第四步：获取访问链接

1. 等待几分钟让GitHub Pages部署完成
2. 在 "Pages" 页面会显示您的网站链接
3. 链接格式：`https://YOUR_USERNAME.github.io/fsupdate-gallery/`

## 📱 分享给微信好友

获得GitHub Pages链接后，您可以直接将链接发送给微信好友：

```
街头篮球7月31日更新文件图片集
https://YOUR_USERNAME.github.io/fsupdate-gallery/
```

## ✨ 功能特点

- 📱 **移动端优化**：完美适配手机屏幕
- 🖼️ **图片展示**：支持筛选、分页、大图预览
- ⚡ **快速加载**：优化的图片加载性能
- 🎨 **美观界面**：现代化的UI设计

## 🔄 更新网站

如果需要更新网站内容：

```bash
# 修改文件后
git add .
git commit -m "更新内容"
git push origin main
```

GitHub Pages会自动重新部署。

## 📞 技术支持

如果遇到问题，请检查：
1. 仓库是否为公开（Public）
2. GitHub Pages是否正确启用
3. 文件路径是否正确

---
*老非制作 | 版本: 5.1.8.0* 