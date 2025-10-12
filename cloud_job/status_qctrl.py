#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
List and monitor Q-CTRL Fire Opal jobs from the last 24 hours

Shows job status, backend, submission time, and completion status
Uses Fire Opal activity_monitor and get_action_metadata APIs

To retrieve results for a specific job:
  Use Action ID with: fo.get_result(action_id)
  Or use: ./retrieve_qctrl_job.py --basePath $basePath --expName <job_name>


Reference: https://docs.q-ctrl.com/fire-opal/execute/submit-jobs/how-to-view-previous-jobs-and-retrieve-results
'''

import os, sys
from pprint import pprint
from datetime import datetime, timedelta
import pytz
import fireopal as fo

import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase output verbosity", default=1)
    parser.add_argument("--limit", type=int, default=20, help="maximum number of jobs to retrieve")
    parser.add_argument("--offset", type=int, default=0, help="skip this many recent jobs")
    parser.add_argument("--status", type=str, default=None, help="filter by status: SUCCESS, FAILURE, PENDING, etc")
    parser.add_argument("--function", type=str, default='all', help="filter by function name (execute, iterate, solve_qaoa) or 'all' for no filter")
    parser.add_argument("--warn", action='store_true', default=False, help="display detailed warning messages at bottom")
    parser.add_argument("--simple", action='store_true', default=False, help="use simple activity_monitor display")

    args = parser.parse_args()
    
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
   
    return args


#...!...!....................
def format_time_ago(timestamp_str):
    """Convert timestamp to human-readable time ago"""
    try:
        if timestamp_str is None:
            return "unknown"
        
        # Parse timestamp string (format: '2025-02-10 23:56:42')
        if isinstance(timestamp_str, str):
            # Try parsing different formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                try:
                    job_time = datetime.strptime(timestamp_str.split('+')[0].replace('Z', ''), fmt)
                    break
                except:
                    continue
            else:
                return timestamp_str
        else:
            return str(timestamp_str)
        
        now = datetime.now()
        diff = now - job_time
        
        if diff.days > 0:
            return f"{diff.days}d {diff.seconds//3600}h ago"
        elif diff.seconds >= 3600:
            return f"{diff.seconds//3600}h {(diff.seconds%3600)//60}m ago"
        elif diff.seconds >= 60:
            return f"{diff.seconds//60}m ago"
        else:
            return f"{diff.seconds}s ago"
    except Exception as e:
        return str(timestamp_str)


#...!...!....................
def classify_warning(warning_msg):
    """Classify warning message into short comment"""
    msg_lower = warning_msg.lower()
    
    if 'measurement error' in msg_lower and 'higher than' in msg_lower:
        return 'High meas error'
    elif 'gate error' in msg_lower and 'higher than' in msg_lower:
        return 'High gate error'
    elif 'readout error' in msg_lower:
        return 'Readout issue'
    elif 'calibration' in msg_lower:
        return 'Calib warning'
    elif 'error rate' in msg_lower:
        return 'High error rate'
    elif 'unavailable' in msg_lower or 'maintenance' in msg_lower:
        return 'Device issue'
    else:
        return 'Warning'


#...!...!....................
def get_job_info(action_id, verb=0):
    """Get number of circuits, backend info, and warnings for a job using Action ID
    
    Returns: (num_circuits, provider, qpu_name, comment, warning_details)
    """
    import warnings
    
    try:
        # Capture warnings during result retrieval
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = fo.get_result(action_id)
            
            num_circuits = 'N/A'
            provider = 'N/A'
            qpu_name = 'N/A'
            
            if 'results' in result:
                num_circuits = len(result['results'])
            
            # Debug: print result keys if very verbose
            if verb > 2:
                print(f'  Debug: result keys for action {action_id}: {list(result.keys())}')
            
            # Extract backend/QPU name from result
            # Fire Opal stores this information at the top level of the result dict
            if 'backend_name' in result:
                qpu_name = result['backend_name']
            elif 'backend' in result:
                qpu_name = result['backend']
            
            # Determine provider from QPU name or provider_job_ids
            if 'provider_job_ids' in result and result['provider_job_ids']:
                # Determine provider from backend name
                if qpu_name.startswith('ibm_'):
                    provider = 'IBM'
                elif 'ionq' in qpu_name.lower():
                    provider = 'IonQ'
                elif 'rigetti' in qpu_name.lower():
                    provider = 'Rigetti'
                else:
                    provider = 'IBM'  # Default assumption for Fire Opal
            
            # Process warnings
            comment = 'OK'
            warning_details = []
            
            if w:
                # Collect all warnings
                for warning in w:
                    warning_msg = str(warning.message)
                    warning_details.append(warning_msg)
                
                # Classify most severe warning for comment
                comment = classify_warning(warning_details[0])
            
            return num_circuits, provider, qpu_name, comment, warning_details
            
    except Exception as e:
        # Job might not be complete yet or inaccessible
        error_msg = str(e).lower()
        if 'not found' in error_msg or 'does not exist' in error_msg:
            return 'N/A', 'N/A', 'N/A', '-', []
        else:
            return 'N/A', 'N/A', 'N/A', 'Error', [str(e)]


#...!...!....................
def convert_utc_to_pt(utc_time_str):
    """Convert UTC timestamp string to Pacific Time
    
    Args:
        utc_time_str: UTC timestamp string (format: '2025-02-10 23:56:42')
    
    Returns:
        Pacific Time string (format: '2025-02-10 15:56:42')
    """
    try:
        # Parse UTC timestamp (format: '2025-02-10 23:56:42')
        utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        
        # Set timezone as UTC
        utc_timezone = pytz.UTC
        utc_dt = utc_timezone.localize(utc_dt)
        
        # Convert to Pacific Time
        pacific = pytz.timezone('America/Los_Angeles')
        pacific_dt = utc_dt.astimezone(pacific)
        
        # Return formatted string without timezone suffix
        return pacific_dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        # If conversion fails, return original
        return utc_time_str


#...!...!....................
def display_jobs_as_table(metadata_list, verb=1):
    """Display jobs in a formatted table
    
    Returns: dict of warnings keyed by action_id
    """
    
    if not metadata_list:
        print('No jobs to display')
        return {}
    
    # Sort by submission time (created_at), most recent first
    sorted_metadata = sorted(metadata_list, key=lambda x: x.created_at, reverse=True)
    
    # Table header with Pacific Time
    print('\n' + '='*140)
    print(f"{'ID':<8} {'Function':<12} {'Submitted (PT)':<22} {'Status':<10} {'Circ':<6} {'Provider':<12} {'QPU':<18} {'Comment':<18}")
    print('='*140)
    
    # Collect warnings for bottom display
    warnings_dict = {}
    
    # Table rows
    for metadata in sorted_metadata:
        action_id = str(metadata.model_id)
        function = metadata.name
        status = metadata.status
        created_utc = metadata.created_at  # In UTC from Fire Opal
        
        # Convert to Pacific Time
        created_pt = convert_utc_to_pt(created_utc)
        
        # Get job info if complete
        if status == 'SUCCESS' and verb > 0:
            num_circuits, provider, qpu_name, comment, warning_details = get_job_info(action_id, verb=verb)
            if warning_details:
                warnings_dict[action_id] = warning_details
        else:
            num_circuits = '-'
            provider = '-'
            qpu_name = '-'
            comment = '-'
        
        # Format: ID, Function, Submitted, Status, Circuits, Provider, QPU, Comment
        print(f"{action_id:<8} {function:<12} {created_pt:<22} {status:<10} {str(num_circuits):<6} {provider:<12} {qpu_name:<18} {comment:<18}")
    
    print('='*140)
    
    return warnings_dict


#...!...!....................
def display_job_metadata(metadata, idx, verb=1):
    """Display formatted information from ActionMetadata object"""
    
    # ActionMetadata attributes: name, status, created_at, updated_at, model_id
    action_id = metadata.model_id
    function = metadata.name
    status = metadata.status
    created = metadata.created_at
    updated = metadata.updated_at
    
    time_ago = format_time_ago(created)
    
    # Display summary
    print(f"\n[{idx}] Action ID: {action_id}")
    print(f"    Function: {function}")
    print(f"    Status: {status}")
    print(f"    Created: {created} ({time_ago})")
    print(f"    Updated: {updated}")
    
    if verb > 1:
        print(f"    Full metadata: {metadata}")


#=================================
#=================================
#  M A I N
#=================================
#=================================
if __name__ == "__main__":
    args = get_parser()
    
    # Authenticate with Q-CTRL
    print('M: authenticating with Q-CTRL Fire Opal ...')
    qctrl_api_key = os.getenv("QCTRL_API_KEY")
    assert qctrl_api_key is not None, "QCTRL_API_KEY environment variable must be set"
    
    fo.authenticate_qctrl_account(api_key=qctrl_api_key)
    print('M: Q-CTRL authentication successful\n')
    
    # Use simple activity_monitor if requested
    if args.simple:
        print('M: displaying Fire Opal activity monitor:\n')
        if args.status:
            fo.activity_monitor(limit=args.limit, offset=args.offset, status=args.status)
        else:
            fo.activity_monitor(limit=args.limit, offset=args.offset)
        print('\nFor more details, run without --simple flag')
        exit(0)
    
    # Get detailed job metadata using get_action_metadata API
    filter_msg = f'limit={args.limit}, offset={args.offset}'
    if args.status:
        filter_msg += f', status={args.status}'
    if args.function != 'all':
        filter_msg += f', function={args.function}'
    
    print(f'M: retrieving Fire Opal job metadata ({filter_msg})...\n')
    
    try:
        # Use Fire Opal's get_action_metadata API
        kwargs = {'limit': args.limit, 'offset': args.offset}
        if args.status:
            kwargs['status'] = args.status
        
        metadata_list = fo.get_action_metadata(**kwargs)
        
        # Filter out show_supported_devices function (not a real job)
        metadata_list = [m for m in metadata_list if m.name != 'show_supported_devices']
        
        # Filter by function name if specified
        if args.function != 'all':
            metadata_list = [m for m in metadata_list if m.name == args.function]
        
    except Exception as e:
        print(f'ERROR: Failed to retrieve job metadata: {str(e)}')
        print('\nTry using --simple flag for basic activity monitor display')
        exit(1)
    
    # Process and display jobs
    if not metadata_list:
        print('No jobs found matching the criteria.')
    else:
        print(f'Found {len(metadata_list)} job(s)')
        
        # Display as table
        warnings_dict = display_jobs_as_table(metadata_list, verb=args.verb)
        
        # Display warnings at the bottom (only if --warn flag is set)
        if warnings_dict and args.warn:
            print('\n' + '='*140)
            print('WARNINGS AND ISSUES:')
            print('='*140)
            for action_id, warning_list in warnings_dict.items():
                print(f"\nJob {action_id}:")
                for i, warning_msg in enumerate(warning_list, 1):
                    # Wrap long warning messages at 135 chars
                    if len(warning_msg) > 135:
                        lines = [warning_msg[i:i+135] for i in range(0, len(warning_msg), 135)]
                        print(f"  [{i}] {lines[0]}")
                        for line in lines[1:]:
                            print(f"      {line}")
                    else:
                        print(f"  [{i}] {warning_msg}")
            print('='*140)
        
        # Detailed view if very verbose
        if args.verb > 2:
            print('\n' + '='*70)
            print('DETAILED VIEW:')
            for idx, metadata in enumerate(metadata_list, 1):
                display_job_metadata(metadata, idx, verb=args.verb)
            print('\n' + '='*70)
        
        # Summary
        status_counts = {}
        for metadata in metadata_list:
            status = metadata.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print('\nSummary:')
        print(f'  Total jobs: {len(metadata_list)}')
        for status, count in sorted(status_counts.items()):
            print(f'  {status}: {count}')
        if warnings_dict:
            print(f'  Jobs with warnings: {len(warnings_dict)}')
            if not args.warn:
                print(f'  (Use --warn flag to see warning details)')
    
    # Only show usage examples if verbose
    if args.verb > 1:
        print('\nTo retrieve results for a specific job:')
        print('  Use Action ID with: fo.get_result(action_id)')
        print('  Or use: ./retrieve_qctrl_job.py --basePath $basePath --expName <job_name>\n')
        
        print('Options:')
        print('  Valid status: SUCCESS, FAILURE, REVOKED, PENDING, RECEIVED, RETRY, STARTED')
        print('  Valid functions: execute, iterate, solve_qaoa, all')
        print('Examples:')
        print('  ./status_qctrl.py --limit 10 --status SUCCESS')
        print('  ./status_qctrl.py --function execute --limit 5 --warn')
        print('  ./status_qctrl.py --function all --status PENDING\n')

