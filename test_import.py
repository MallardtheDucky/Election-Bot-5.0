#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from cogs.all_winners import AllWinners
    print("✓ Successfully imported AllWinners")
    
    # Create a mock bot
    class MockBot:
        def __init__(self):
            self.db = {}
    
    bot = MockBot()
    cog = AllWinners(bot)
    print("✓ Successfully created AllWinners instance")
    
    # Check if the methods exist
    if hasattr(cog, 'view_general_campaign'):
        print("✓ view_general_campaign method exists")
    else:
        print("❌ view_general_campaign method missing")
        
    if hasattr(cog, 'admin_view_all_campaign_points'):
        print("✓ admin_view_all_campaign_points method exists")
    else:
        print("❌ admin_view_all_campaign_points method missing")
        
    # Check all methods in the cog
    methods = [name for name in dir(cog) if not name.startswith('_') and callable(getattr(cog, name))]
    print(f"\nAll methods in cog ({len(methods)}):")
    for method in sorted(methods):
        print(f"  - {method}")
        
except Exception as e:
    print(f"❌ Error importing: {e}")
    import traceback
    traceback.print_exc()