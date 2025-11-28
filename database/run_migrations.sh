#!/bin/bash

# HVAC Lead Generation Platform - Database Migration Script
# This script runs all migrations in the correct order for Supabase/PostgreSQL

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}HVAC Lead Gen - Database Migrations${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Warning: DATABASE_URL not set${NC}"
    echo "Please set it with your Supabase connection string:"
    echo "export DATABASE_URL='postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres'"
    echo ""
    echo "You can find this in:"
    echo "Supabase Dashboard → Settings → Database → Connection String"
    echo ""
    read -p "Do you want to enter it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter DATABASE_URL: " DATABASE_URL
        export DATABASE_URL
    else
        echo -e "${RED}Aborted. Please set DATABASE_URL and try again.${NC}"
        exit 1
    fi
fi

# Verify psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql not found${NC}"
    echo "Please install PostgreSQL client tools:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    echo "  Windows: Download from https://www.postgresql.org/download/windows/"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

echo -e "${YELLOW}Using migrations from:${NC} $MIGRATIONS_DIR"
echo ""

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection successful${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
    echo "Please check your DATABASE_URL and try again."
    exit 1
fi
echo ""

# Run migrations in order
MIGRATIONS=(
    "001_create_agencies.sql"
    "002_create_counties.sql"
    "003_create_permits.sql"
    "004_create_leads.sql"
    "005_create_sync_config.sql"
    "006_create_indexes.sql"
)

echo -e "${GREEN}Running migrations...${NC}"
echo ""

for migration in "${MIGRATIONS[@]}"; do
    MIGRATION_PATH="$MIGRATIONS_DIR/$migration"

    if [ ! -f "$MIGRATION_PATH" ]; then
        echo -e "${RED}✗ Migration not found: $migration${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Running: $migration${NC}"

    if psql "$DATABASE_URL" -f "$MIGRATION_PATH" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $migration completed${NC}"
    else
        echo -e "${RED}✗ $migration failed${NC}"
        echo "Run this for details:"
        echo "psql \$DATABASE_URL -f $MIGRATION_PATH"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}All migrations completed successfully!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Ask about seeding
read -p "Do you want to load seed data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SEED_PATH="$SCRIPT_DIR/seed.sql"

    if [ ! -f "$SEED_PATH" ]; then
        echo -e "${RED}✗ Seed file not found: $SEED_PATH${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}Loading seed data...${NC}"

    if psql "$DATABASE_URL" -f "$SEED_PATH"; then
        echo ""
        echo -e "${GREEN}✓ Seed data loaded successfully${NC}"
    else
        echo -e "${RED}✗ Seed data failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Database setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Verify tables in Supabase Dashboard → Table Editor"
echo "2. Configure backend with DATABASE_URL"
echo "3. Test API endpoints"
echo ""
