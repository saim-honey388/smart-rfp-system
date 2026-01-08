"""
Column Classifier Service

Classifies columns in comparison matrix as 'fixed' or 'vendor' using:
1. Majority voting - if >50% of vendors match RFP value, column is fixed
2. AI semantic check - for ambiguous text columns
3. Caching - store classification in DB to avoid repeated AI calls
"""

from typing import List, Dict, Any, Optional, Tuple
import json


def normalize_value(val: Any) -> str:
    """Normalize value for comparison (handle None, TBD, whitespace)."""
    if val is None:
        return ""
    s = str(val).strip().upper()
    if s in ('TBD', 'N/A', '-', '$-', '', 'NOT QUOTED'):
        return ""
    return s


def classify_columns_majority_voting(
    rfp_rows: List[dict],
    vendor_proposals: List[dict],  # Each has {id, proposal_form_data}
    threshold: float = 0.5
) -> Tuple[List[str], List[str], List[str]]:
    """
    Classify columns using majority voting.
    
    Args:
        rfp_rows: List of RFP proposal form rows
        vendor_proposals: List of proposals with form data
        threshold: Minimum percentage for majority (0.5 = 50%)
        
    Returns:
        (fixed_columns, vendor_columns, ambiguous_columns)
    """
    if not rfp_rows:
        return [], [], []
    
    # Get all column names from RFP rows
    sample_row = rfp_rows[0]
    all_columns = [k for k in sample_row.keys() if k not in ('values',)]
    
    # Filter to proposals with actual form data
    proposals_with_data = [p for p in vendor_proposals if p.get('proposal_form_data')]
    
    if not proposals_with_data:
        # No vendor data, treat all as fixed (show RFP values only)
        return all_columns, [], []
    
    fixed_columns = []
    vendor_columns = []
    ambiguous_columns = []
    
    def get_vendor_row(proposal: dict, item_id: str) -> Optional[dict]:
        """Find vendor row matching RFP item_id."""
        for row in proposal.get('proposal_form_data', []):
            if str(row.get('item_id', '')).strip() == str(item_id).strip():
                return row
        return None
    
    for col in all_columns:
        total_comparisons = 0
        match_count = 0
        
        for rfp_row in rfp_rows:
            rfp_value = normalize_value(rfp_row.get(col))
            if not rfp_value:
                continue  # Skip empty RFP values
            
            for p in proposals_with_data:
                vendor_row = get_vendor_row(p, rfp_row.get('item_id'))
                if vendor_row:
                    vendor_value = normalize_value(vendor_row.get(col))
                    if vendor_value:  # Only count non-empty vendor values
                        total_comparisons += 1
                        if rfp_value == vendor_value:
                            match_count += 1
        
        # Classify based on match ratio
        if total_comparisons == 0:
            # No valid comparisons, default to fixed
            fixed_columns.append(col)
        else:
            match_ratio = match_count / total_comparisons
            if match_ratio > threshold:
                fixed_columns.append(col)
            elif match_ratio < (1 - threshold):
                # Clear majority says different
                vendor_columns.append(col)
            else:
                # Ambiguous - needs AI check
                ambiguous_columns.append(col)
    
    return fixed_columns, vendor_columns, ambiguous_columns


async def ai_semantic_classify(
    column_name: str,
    rfp_sample_values: List[str],
    vendor_sample_values: List[str]
) -> str:
    """
    Use AI to semantically classify an ambiguous column.
    
    Returns: 'fixed' or 'vendor'
    """
    from backend.src.utils.ai_client import get_chat_llm
    
    llm = get_chat_llm(model="gpt-4o", temperature=0)
    
    prompt = f"""You are classifying a column in a proposal comparison matrix.

Column Name: {column_name}

Sample values from RFP template:
{rfp_sample_values[:5]}

Sample values from vendor proposals:
{vendor_sample_values[:10]}

Question: Should this column be classified as:
- FIXED: Values are semantically the same across RFP and vendors (identifiers, descriptions that should match)
- VENDOR: Values represent vendor-specific data (prices, quantities, dates that vary by vendor)

Consider:
1. If values look like minor text variations of the same thing → FIXED
2. If values are clearly different amounts/prices/quantities → VENDOR
3. If column name suggests pricing/cost/quantity → VENDOR
4. If column name suggests identifier/description/scope → FIXED

Respond with exactly one word: FIXED or VENDOR"""

    try:
        response = await llm.ainvoke(prompt)
        result = response.content.strip().upper()
        return 'fixed' if 'FIXED' in result else 'vendor'
    except Exception as e:
        print(f"AI classification failed for {column_name}: {e}")
        # Default to vendor (safer - shows all values)
        return 'vendor'


async def classify_with_ai_fallback(
    rfp_rows: List[dict],
    vendor_proposals: List[dict],
    threshold: float = 0.5
) -> Tuple[List[str], List[str]]:
    """
    Full classification: majority voting + AI fallback for ambiguous columns.
    
    Returns:
        (fixed_columns, vendor_columns)
    """
    fixed, vendor, ambiguous = classify_columns_majority_voting(
        rfp_rows, vendor_proposals, threshold
    )
    
    # Process ambiguous columns with AI
    for col in ambiguous:
        # Collect sample values
        rfp_samples = [str(row.get(col, '')) for row in rfp_rows[:5] if row.get(col)]
        
        vendor_samples = []
        for p in vendor_proposals:
            for row in (p.get('proposal_form_data') or [])[:5]:
                if row.get(col):
                    vendor_samples.append(str(row.get(col)))
        
        classification = await ai_semantic_classify(col, rfp_samples, vendor_samples)
        
        if classification == 'fixed':
            fixed.append(col)
        else:
            vendor.append(col)
    
    return fixed, vendor


def get_cached_classification(rfp_cache: dict, current_proposal_ids: List[str]) -> Optional[Tuple[List[str], List[str]]]:
    """
    Check if cached classification is still valid.
    
    Returns:
        (fixed_columns, vendor_columns) if cache valid, None otherwise
    """
    if not rfp_cache:
        return None
    
    cached_ids = sorted(rfp_cache.get('proposal_ids', []))
    current_ids = sorted(current_proposal_ids)
    
    if cached_ids != current_ids:
        return None  # Cache invalidated
    
    return (
        rfp_cache.get('fixed_columns', []),
        rfp_cache.get('vendor_columns', [])
    )


def build_cache(fixed_columns: List[str], vendor_columns: List[str], proposal_ids: List[str]) -> dict:
    """Build cache dictionary to store."""
    return {
        'proposal_ids': sorted(proposal_ids),
        'fixed_columns': fixed_columns,
        'vendor_columns': vendor_columns
    }
