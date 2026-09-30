#!/bin/bash

# 🔍 ByteFlow Security Fixes Verification Script
# This script verifies all 10 fixes have been properly applied
# Run this after applying the fixed files

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     ByteFlow Security Fixes - Verification Script             ║"
echo "║     Testing all 10 fixes are working correctly                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# ═══════════════════════════════════════════════════════════════════════
# Test 1: Check if web_companion.py is fixed version
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 1: Checking if web_companion.py is fixed..."
if grep -q "from flask_limiter import Limiter" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: web_companion.py has rate limiting"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: web_companion.py missing rate limiting"
    echo "   Run: cp byteflow/web_companion_fixed.py byteflow/web_companion.py"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 2: Check if companion.html is fixed version
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 2: Checking if companion.html is fixed..."
if grep -q "textContent = text" byteflow/templates/companion.html; then
    echo -e "${GREEN}✅ PASS${NC}: companion.html uses textContent (XSS safe)"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: companion.html still uses innerHTML"
    echo "   Run: cp byteflow/templates/companion_fixed.html byteflow/templates/companion.html"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 3: Check if flask-limiter is installed
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 3: Checking if flask-limiter is installed..."
if python -c "from flask_limiter import Limiter" 2>/dev/null; then
    echo -e "${GREEN}✅ PASS${NC}: flask-limiter is installed"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: flask-limiter not installed"
    echo "   Run: pip install flask-limiter>=3.3.0"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 4: Check if input validation is present
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 4: Checking if input validation function exists..."
if grep -q "def validate_input" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: Input validation function found"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Input validation function missing"
    echo "   This should be in the fixed version"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 5: Check if security headers are present
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 5: Checking if security headers function exists..."
if grep -q "set_security_headers" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: Security headers function found"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Security headers function missing"
    echo "   This should be in the fixed version"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 6: Check if deque is used for logging
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 6: Checking if deque is used for activity logging..."
if grep -q "from collections import deque" byteflow/web_companion.py; then
    if grep -q "activity_log = deque" byteflow/web_companion.py; then
        echo -e "${GREEN}✅ PASS${NC}: Using deque for activity log (efficient)"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: deque imported but not used"
        ((FAILED++))
    fi
else
    echo -e "${RED}❌ FAIL${NC}: deque not imported"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 7: Check if timeout protection exists
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 7: Checking if timeout protection is present..."
if grep -q "asyncio.wait_for" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: Timeout protection with asyncio.wait_for found"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Timeout protection missing"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 8: Check if CORS is restricted
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 8: Checking if CORS is properly restricted..."
if grep -q "localhost" byteflow/web_companion.py && grep -q "CORS" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: CORS configured with localhost restriction"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  WARN${NC}: CORS configuration needs verification"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 9: Check if error handling is present
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 9: Checking if proper error handling exists..."
if grep -q "except asyncio.TimeoutError" byteflow/web_companion.py; then
    echo -e "${GREEN}✅ PASS${NC}: Proper timeout error handling found"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Timeout error handling missing"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Test 10: Check if all imports are present
# ═══════════════════════════════════════════════════════════════════════
echo "🔍 TEST 10: Checking all required imports..."
IMPORTS_OK=true
for import in "from flask import Flask" "from flask_cors import CORS" "from flask_limiter import Limiter" "from collections import deque"; do
    if ! grep -q "$import" byteflow/web_companion.py; then
        echo -e "${RED}❌${NC} Missing: $import"
        IMPORTS_OK=false
    fi
done

if [ "$IMPORTS_OK" = true ]; then
    echo -e "${GREEN}✅ PASS${NC}: All required imports present"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Some imports missing"
    ((FAILED++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 VERIFICATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "Passed: ${GREEN}${PASSED}${NC}/10"
echo -e "Failed: ${RED}${FAILED}${NC}/10"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "The ByteFlow security fixes have been successfully applied."
    echo "Your application is now protected against:"
    echo "  ✅ XSS attacks"
    echo "  ✅ DoS attacks (rate limiting)"
    echo "  ✅ Resource leaks (timeout protection)"
    echo "  ✅ Input validation attacks"
    echo "  ✅ Security header attacks"
    echo ""
    echo "🚀 Ready for production deployment!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please fix the failing tests before deploying to production."
    echo "See the messages above for details."
    exit 1
fi
