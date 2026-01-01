#!/bin/bash

# Script to clean up old .sh files and pull latest code

echo "Step 1: Removing old .sh files that are no longer needed..."
rm -f COMPLETE_FIX.sh \
      DEPLOYMENT.md \
      FIREWALL_SETUP.md \
      FIX_LOGIN.sh \
      FORCE_RESTART_FRONTEND.sh \
      QUICK_FIX.md \
      check_external_access.sh \
      check_mongo_auth.sh \
      check_nginx_logs.sh \
      check_status.sh \
      diagnose_access.sh \
      final_check.sh \
      fix_and_start.sh \
      fix_frontend_api.sh \
      hackingpanel-backend.service \
      hackingpanel-frontend.service \
      manage_services.sh \
      restart_with_env.sh \
      setup_nginx.sh \
      setup_systemd.sh \
      start_all.sh \
      start_frontend.sh \
      start_production.sh \
      start_server.sh \
      stop_all.sh \
      test_login_direct.sh \
      test_nginx.sh \
      update_env.sh \
      update_frontend_env.sh \
      verify_and_fix.sh

echo "Step 2: Discarding local changes to allow pull..."
git checkout -- COMPLETE_FIX.sh FORCE_RESTART_FRONTEND.sh test_login_direct.sh 2>/dev/null || true

echo "Step 3: Pulling latest code from GitHub..."
git pull origin main

echo "Step 4: Making start.sh executable..."
chmod +x start.sh

echo ""
echo "Done! Now you can run: ./start.sh"

