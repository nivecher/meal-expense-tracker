#!/bin/bash
# ============================================
# Simplified Build Script
# ============================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TARGET="development"
TAG="latest"
PLATFORM="linux/amd64"
PUSH=false
LOAD=true

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --target TARGET    Build target (development|production|lambda) [default: development]"
    echo "  -g, --tag TAG         Image tag [default: latest]"
    echo "  -p, --platform PLATFORM Platform (linux/amd64|linux/arm64|linux/amd64,linux/arm64) [default: linux/amd64]"
    echo "  --push                Push to registry (requires registry setup)"
    echo "  --no-load             Don't load image into local Docker"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Build development image"
    echo "  $0 -t production -g v1.0.0          # Build production image with tag v1.0.0"
    echo "  $0 -t lambda -p linux/arm64          # Build lambda image for ARM64"
    echo "  $0 -p linux/amd64,linux/arm64 --push # Build and push multi-platform image"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -g|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            LOAD=false
            shift
            ;;
        --no-load)
            LOAD=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate target
case $TARGET in
    development|production|lambda)
        ;;
    *)
        echo -e "${RED}❌ Invalid target: $TARGET${NC}"
        echo "Valid targets: development, production, lambda"
        exit 1
        ;;
esac

# Build command
BUILD_CMD="docker buildx build --platform $PLATFORM --target $TARGET -t meal-expense-tracker:$TAG"

# Add push or load
if [ "$PUSH" = true ]; then
    BUILD_CMD="$BUILD_CMD --push"
elif [ "$LOAD" = true ]; then
    BUILD_CMD="$BUILD_CMD --load"
fi

# Add context
BUILD_CMD="$BUILD_CMD ."

echo -e "${BLUE}🔨 Building Docker image...${NC}"
echo -e "${BLUE}   Target: ${YELLOW}$TARGET${NC}"
echo -e "${BLUE}   Tag: ${YELLOW}$TAG${NC}"
echo -e "${BLUE}   Platform: ${YELLOW}$PLATFORM${NC}"
echo -e "${BLUE}   Command: ${YELLOW}$BUILD_CMD${NC}"
echo ""

# Execute build
if eval $BUILD_CMD; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"

    if [ "$LOAD" = true ]; then
        echo -e "${BLUE}📦 Image loaded into local Docker${NC}"
        echo -e "${BLUE}   Run with: ${YELLOW}docker run -p 8000:5000 meal-expense-tracker:$TAG${NC}"
    fi

    if [ "$PUSH" = true ]; then
        echo -e "${BLUE}🚀 Image pushed to registry${NC}"
    fi
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi
