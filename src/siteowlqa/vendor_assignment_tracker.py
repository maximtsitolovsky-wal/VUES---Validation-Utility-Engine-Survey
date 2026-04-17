"""
Vendor Assignment Tracker
==========================
Reads vendor assignments from Excel and compares with Scout Airtable completions
to track remaining assignments and completion velocity.

Features:
- Load vendor assignments from Excel workbook
- Compare against Scout Airtable completed submissions
- Calculate remaining assignments per vendor
- Track completion velocity (time / total assignments)
- Provide vendor performance insights for dashboard and weekly highlights
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import openpyxl

logger = logging.getLogger(__name__)


@dataclass
class VendorAssignment:
    """Represents a vendor assignment from the Excel file."""
    site_number: str
    vendor_name: str
    assigned_date: Optional[datetime] = None
    
    
@dataclass
class VendorStats:
    """Statistics for a single vendor."""
    vendor_name: str
    total_assigned: int
    completed: int
    remaining: int
    completion_rate: float  # percentage
    avg_completion_days: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "vendor_name": self.vendor_name,
            "total_assigned": self.total_assigned,
            "completed": self.completed,
            "remaining": self.remaining,
            "completion_rate": round(self.completion_rate, 2),
            "avg_completion_days": round(self.avg_completion_days, 2) if self.avg_completion_days else None
        }


class VendorAssignmentTracker:
    """Tracks vendor assignments and completion progress."""
    
    # Known vendor names (normalized)
    KNOWN_VENDORS = ["Wachter", "Techwise", "SAS", "Everon", "CEI"]
    
    def __init__(self, assignment_file_path: str):
        """
        Initialize tracker with path to vendor assignment Excel file.
        
        Args:
            assignment_file_path: Path to the vendor assignment Excel file
        """
        self.assignment_file = Path(assignment_file_path)
        self.assignments: List[VendorAssignment] = []
        self._loaded = False
    
    def load_assignments(self, sheet_name: str = "Sheet1") -> bool:
        """
        Load vendor assignments from Excel file.
        
        Args:
            sheet_name: Name of the sheet containing assignments
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.assignment_file.exists():
            logger.error(f"Assignment file not found: {self.assignment_file}")
            return False
        
        try:
            logger.info(f"Loading vendor assignments from {self.assignment_file.name}...")
            wb = openpyxl.load_workbook(self.assignment_file, data_only=True)
            
            # Try to find the correct sheet
            if sheet_name not in wb.sheetnames:
                # Try first sheet
                sheet_name = wb.sheetnames[0]
                logger.warning(f"Sheet not found, using first sheet: {sheet_name}")
            
            ws = wb[sheet_name]
            
            # Find header row (look for "Site Number" or "Store Number" and "Vendor")
            header_row = None
            site_col_idx = None
            vendor_col_idx = None
            date_col_idx = None
            
            for row_idx in range(1, min(21, ws.max_row + 1)):
                for col_idx in range(1, min(21, ws.max_column + 1)):
                    cell_value = ws.cell(row_idx, col_idx).value
                    if cell_value:
                        cell_str = str(cell_value).strip().lower()
                        
                        if "site" in cell_str or "store" in cell_str:
                            if "number" in cell_str:
                                header_row = row_idx
                                site_col_idx = col_idx
                        elif "vendor" in cell_str or "company" in cell_str:
                            vendor_col_idx = col_idx
                        elif "date" in cell_str or "assigned" in cell_str:
                            date_col_idx = col_idx
                
                if header_row and site_col_idx and vendor_col_idx:
                    break
            
            if not (header_row and site_col_idx and vendor_col_idx):
                logger.error(f"Could not find required columns. Site={site_col_idx}, Vendor={vendor_col_idx}")
                wb.close()
                return False
            
            logger.info(f"Found headers at row {header_row}: Site col={site_col_idx}, Vendor col={vendor_col_idx}")
            
            # Load assignments
            assignments_loaded = 0
            for row_idx in range(header_row + 1, ws.max_row + 1):
                site_num = ws.cell(row_idx, site_col_idx).value
                vendor = ws.cell(row_idx, vendor_col_idx).value
                assigned_date = ws.cell(row_idx, date_col_idx).value if date_col_idx else None
                
                if site_num and vendor:
                    site_num_str = str(site_num).strip()
                    vendor_str = self._normalize_vendor_name(str(vendor).strip())
                    
                    # Parse date if available
                    date_obj = None
                    if assigned_date:
                        if isinstance(assigned_date, datetime):
                            date_obj = assigned_date
                        elif isinstance(assigned_date, str):
                            try:
                                date_obj = datetime.strptime(assigned_date, "%Y-%m-%d")
                            except ValueError:
                                try:
                                    date_obj = datetime.strptime(assigned_date, "%m/%d/%Y")
                                except ValueError:
                                    pass
                    
                    self.assignments.append(VendorAssignment(
                        site_number=site_num_str,
                        vendor_name=vendor_str,
                        assigned_date=date_obj
                    ))
                    assignments_loaded += 1
            
            wb.close()
            logger.info(f"Loaded {assignments_loaded} vendor assignments")
            self._loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading vendor assignments: {e}")
            return False
    
    def _normalize_vendor_name(self, vendor: str) -> str:
        """Normalize vendor name to match known vendors."""
        vendor_upper = vendor.upper()
        
        for known in self.KNOWN_VENDORS:
            if known.upper() in vendor_upper:
                return known
        
        return vendor  # Return as-is if not recognized
    
    def calculate_vendor_stats(
        self, 
        completed_submissions: List[dict]
    ) -> Dict[str, VendorStats]:
        """
        Calculate statistics for each vendor based on assignments and completions.
        
        Args:
            completed_submissions: List of completed Scout submissions from Airtable.
                Each dict should have: site_number, vendor_name, submitted_at
        
        Returns:
            Dictionary mapping vendor name to VendorStats
        """
        if not self._loaded:
            logger.warning("Assignments not loaded yet")
            return {}
        
        # Build completion map by site number
        completion_map = {}
        for sub in completed_submissions:
            site_num = str(sub.get("site_number", "")).strip()
            vendor = self._normalize_vendor_name(str(sub.get("vendor_name", "")).strip())
            submitted_at = sub.get("submitted_at")
            
            if site_num:
                completion_map[site_num] = {
                    "vendor": vendor,
                    "submitted_at": submitted_at
                }
        
        # Group assignments by vendor
        vendor_assignments: Dict[str, List[VendorAssignment]] = {}
        for assignment in self.assignments:
            vendor = assignment.vendor_name
            if vendor not in vendor_assignments:
                vendor_assignments[vendor] = []
            vendor_assignments[vendor].append(assignment)
        
        # Calculate stats for each vendor
        vendor_stats = {}
        
        for vendor, assignments in vendor_assignments.items():
            total_assigned = len(assignments)
            completed_count = 0
            completion_days = []
            
            for assignment in assignments:
                if assignment.site_number in completion_map:
                    completed_count += 1
                    
                    # Calculate completion time if we have dates
                    if assignment.assigned_date:
                        completion_info = completion_map[assignment.site_number]
                        submitted_at = completion_info.get("submitted_at")
                        
                        if submitted_at:
                            if isinstance(submitted_at, str):
                                try:
                                    submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                                except:
                                    try:
                                        submitted_at = datetime.strptime(submitted_at, "%Y-%m-%d")
                                    except:
                                        submitted_at = None
                            
                            if submitted_at:
                                days = (submitted_at - assignment.assigned_date).days
                                if days >= 0:  # Only count positive days
                                    completion_days.append(days)
            
            remaining = total_assigned - completed_count
            completion_rate = (completed_count / total_assigned * 100) if total_assigned > 0 else 0.0
            avg_days = sum(completion_days) / len(completion_days) if completion_days else None
            
            vendor_stats[vendor] = VendorStats(
                vendor_name=vendor,
                total_assigned=total_assigned,
                completed=completed_count,
                remaining=remaining,
                completion_rate=completion_rate,
                avg_completion_days=avg_days
            )
        
        return vendor_stats
    
    def get_summary(self) -> dict:
        """Get summary of all assignments."""
        if not self._loaded:
            return {
                "total_assignments": 0,
                "vendors": [],
                "loaded": False
            }
        
        vendor_counts = {}
        for assignment in self.assignments:
            vendor = assignment.vendor_name
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        return {
            "total_assignments": len(self.assignments),
            "vendors": [
                {"name": vendor, "assignments": count}
                for vendor, count in sorted(vendor_counts.items(), key=lambda x: -x[1])
            ],
            "loaded": True
        }
