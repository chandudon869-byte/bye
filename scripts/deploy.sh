# 1. Push to GitHub
git add .
git commit -m "Initial production pipeline"
git push origin main

# 2. In Render Dashboard:
#    - Click "New +" → "Blueprint"
#    - Connect your repository
#    - Render will automatically detect render.yaml
#    - Click "Apply"

# 3. Wait for deployment (5-10 minutes)

# 4. Test the API
curl https://nepse-api.onrender.com/health
curl https://nepse-api.onrender.com/api/v1/ipos?status=upcoming