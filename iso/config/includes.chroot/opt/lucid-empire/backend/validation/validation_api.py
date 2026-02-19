# LUCID EMPIRE - Validation API Endpoints
# FastAPI endpoints for forensic validation integration

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import json
import time
from datetime import datetime

from .forensic_validator import ForensicValidator, ValidationTool, ValidationResult

router = APIRouter(prefix="/api/validation", tags=["validation"])

class ValidationRequest(BaseModel):
    profile_id: Optional[str] = None
    tools: Optional[List[str]] = None
    run_immediately: bool = True

class ValidationResponse(BaseModel):
    status: str
    message: str
    validation_id: Optional[str] = None
    results: Optional[Dict] = None

class ValidationStatusResponse(BaseModel):
    validation_id: str
    status: str
    progress: float
    current_tool: Optional[str] = None
    results: Optional[Dict] = None
    errors: Optional[List[str]] = None

# Global validator instance
validator = ForensicValidator()
validation_tasks = {}

@router.post("/run", response_model=ValidationResponse)
async def run_validation(request: ValidationRequest):
    """
    Run comprehensive forensic validation
    """
    try:
        # Generate validation ID
        validation_id = f"validation_{int(time.time())}"
        
        # Determine which tools to run
        tools = []
        if request.tools:
            tool_map = {
                "creepjs": ValidationTool.CREEPJS,
                "pixelscan": ValidationTool.PIXELSCAN,
                "iphey": ValidationTool.IPHEY,
                "fingerprintjs": ValidationTool.FINGERPRINTJS,
                "amiunique": ValidationTool.AMIUNIQUE
            }
            tools = [tool_map.get(tool.lower()) for tool in request.tools if tool.lower() in tool_map]
        else:
            tools = list(ValidationTool)
        
        # Initialize task status
        validation_tasks[validation_id] = {
            "status": "running",
            "progress": 0.0,
            "current_tool": None,
            "results": {},
            "errors": [],
            "start_time": datetime.now()
        }
        
        if request.run_immediately:
            # Run validation in background
            asyncio.create_task(run_validation_background(validation_id, request.profile_id, tools))
            
            return ValidationResponse(
                status="started",
                message=f"Validation started with ID: {validation_id}",
                validation_id=validation_id
            )
        else:
            # Queue validation (for future implementation)
            return ValidationResponse(
                status="queued",
                message=f"Validation queued with ID: {validation_id}",
                validation_id=validation_id
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start validation: {str(e)}")

@router.get("/status/{validation_id}", response_model=ValidationStatusResponse)
async def get_validation_status(validation_id: str):
    """
    Get validation status and results
    """
    if validation_id not in validation_tasks:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    task = validation_tasks[validation_id]
    
    return ValidationStatusResponse(
        validation_id=validation_id,
        status=task["status"],
        progress=task["progress"],
        current_tool=task["current_tool"],
        results=task["results"] if task["status"] == "completed" else None,
        errors=task["errors"] if task["errors"] else None
    )

@router.get("/results/{validation_id}")
async def get_validation_results(validation_id: str):
    """
    Get detailed validation results
    """
    if validation_id not in validation_tasks:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    task = validation_tasks[validation_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Validation not completed")
    
    return {
        "validation_id": validation_id,
        "status": task["status"],
        "results": task["results"],
        "summary": generate_summary(task["results"]),
        "completed_at": task.get("completed_at"),
        "duration_seconds": (task.get("completed_at", datetime.now()) - task["start_time"]).total_seconds()
    }

@router.get("/history")
async def get_validation_history():
    """
    Get history of recent validations
    """
    history = []
    
    for validation_id, task in validation_tasks.items():
        history.append({
            "validation_id": validation_id,
            "status": task["status"],
            "progress": task["progress"],
            "start_time": task["start_time"].isoformat(),
            "completed_at": task.get("completed_at", "").isoformat() if task.get("completed_at") else None,
            "overall_score": calculate_overall_score(task["results"]) if task["results"] else None
        })
    
    # Sort by start time (most recent first)
    history.sort(key=lambda x: x["start_time"], reverse=True)
    
    return {
        "history": history,
        "total_validations": len(history)
    }

@router.delete("/results/{validation_id}")
async def delete_validation_results(validation_id: str):
    """
    Delete validation results
    """
    if validation_id not in validation_tasks:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    del validation_tasks[validation_id]
    
    return {
        "status": "deleted",
        "message": f"Validation {validation_id} deleted successfully"
    }

@router.get("/tools")
async def get_available_tools():
    """
    Get list of available validation tools
    """
    tools = []
    for tool in ValidationTool:
        tools.append({
            "name": tool.value,
            "display_name": tool.value.title().replace("Js", "JS"),
            "description": get_tool_description(tool),
            "category": get_tool_category(tool)
        })
    
    return {
        "tools": tools,
        "total_count": len(tools)
    }

@router.get("/profiles")
async def get_validation_profiles():
    """
    Get list of profiles available for validation
    """
    try:
        # Get profiles from main API
        import requests
        response = requests.get("http://localhost:8000/api/aged-profiles", timeout=5)
        
        if response.status_code == 200:
            profiles = response.json().get("profiles", [])
            return {
                "profiles": profiles,
                "total_count": len(profiles)
            }
        else:
            return {
                "profiles": [],
                "total_count": 0,
                "error": "Failed to fetch profiles"
            }
    except Exception as e:
        return {
            "profiles": [],
            "total_count": 0,
            "error": str(e)
        }

@router.post("/compare")
async def compare_validations(validation_ids: List[str]):
    """
    Compare multiple validation results
    """
    results = {}
    
    for validation_id in validation_ids:
        if validation_id not in validation_tasks:
            raise HTTPException(status_code=404, detail=f"Validation {validation_id} not found")
        
        task = validation_tasks[validation_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Validation {validation_id} not completed")
        
        results[validation_id] = task["results"]
    
    # Generate comparison
    comparison = generate_comparison(results)
    
    return {
        "comparison": comparison,
        "summary": {
            "total_validations": len(validation_ids),
            "average_score": comparison.get("average_score", 0),
            "best_score": comparison.get("best_score", 0),
            "worst_score": comparison.get("worst_score", 0)
        }
    }

@router.get("/export/{validation_id}")
async def export_validation_results(validation_id: str, format: str = "json"):
    """
    Export validation results in specified format
    """
    if validation_id not in validation_tasks:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    task = validation_tasks[validation_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Validation not completed")
    
    if format.lower() == "json":
        return {
            "validation_id": validation_id,
            "export_format": "json",
            "data": task["results"],
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "validation_id": validation_id,
                "total_tools": len(task["results"])
            }
        }
    elif format.lower() == "csv":
        # Generate CSV format
        csv_data = generate_csv_export(task["results"])
        return {
            "validation_id": validation_id,
            "export_format": "csv",
            "data": csv_data,
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "validation_id": validation_id
            }
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")

# Background task function
async def run_validation_background(validation_id: str, profile_id: Optional[str], tools: List[ValidationTool]):
    """
    Run validation in background
    """
    try:
        task = validation_tasks[validation_id]
        total_tools = len(tools)
        
        for i, tool in enumerate(tools):
            # Update progress
            task["current_tool"] = tool.value
            task["progress"] = (i / total_tools) * 100
            
            # Run validation for this tool
            try:
                result = await validator._validate_with_tool(tool, profile_id)
                task["results"][tool.value] = {
                    "score": result.score,
                    "trust_score": result.trust_score,
                    "warnings": result.warnings,
                    "errors": result.errors,
                    "recommendations": result.recommendations,
                    "raw_data": result.raw_data
                }
            except Exception as e:
                task["errors"].append(f"{tool.value}: {str(e)}")
                task["results"][tool.value] = {
                    "score": 0,
                    "trust_score": "ERROR",
                    "warnings": [],
                    "errors": [str(e)],
                    "recommendations": ["Check tool configuration"],
                    "raw_data": {}
                }
        
        # Mark as completed
        task["status"] = "completed"
        task["progress"] = 100.0
        task["current_tool"] = None
        task["completed_at"] = datetime.now()
        
    except Exception as e:
        task["status"] = "failed"
        task["errors"].append(f"Validation failed: {str(e)}")
        task["completed_at"] = datetime.now()

# Helper functions
def generate_summary(results: Dict) -> Dict:
    """Generate summary of validation results"""
    scores = [tool_result.get("score", 0) for tool_result in results.values()]
    overall_score = sum(scores) / len(scores) if scores else 0
    
    passed = sum(1 for score in scores if score >= 80)
    total = len(scores)
    
    critical_issues = sum(len(tool_result.get("errors", [])) for tool_result in results.values())
    
    return {
        "overall_score": overall_score,
        "tools_passed": passed,
        "total_tools": total,
        "critical_issues": critical_issues,
        "status": "excellent" if overall_score >= 85 else "good" if overall_score >= 70 else "fair" if overall_score >= 50 else "poor"
    }

def calculate_overall_score(results: Dict) -> float:
    """Calculate overall score from results"""
    scores = [tool_result.get("score", 0) for tool_result in results.values()]
    return sum(scores) / len(scores) if scores else 0

def generate_comparison(results: Dict[str, Dict]) -> Dict:
    """Generate comparison between multiple validation results"""
    comparison = {
        "tools": {},
        "overall_scores": {},
        "best_validation": None,
        "worst_validation": None
    }
    
    # Calculate scores for each validation
    for validation_id, validation_results in results.items():
        overall_score = calculate_overall_score(validation_results)
        comparison["overall_scores"][validation_id] = overall_score
        
        # Compare individual tools
        for tool_name, tool_result in validation_results.items():
            if tool_name not in comparison["tools"]:
                comparison["tools"][tool_name] = {}
            
            comparison["tools"][tool_name][validation_id] = tool_result.get("score", 0)
    
    # Find best and worst validations
    if comparison["overall_scores"]:
        best_id = max(comparison["overall_scores"], key=comparison["overall_scores"].get)
        worst_id = min(comparison["overall_scores"], key=comparison["overall_scores"].get)
        
        comparison["best_validation"] = {
            "validation_id": best_id,
            "score": comparison["overall_scores"][best_id]
        }
        comparison["worst_validation"] = {
            "validation_id": worst_id,
            "score": comparison["overall_scores"][worst_id]
        }
    
    # Calculate averages
    all_scores = list(comparison["overall_scores"].values())
    comparison["average_score"] = sum(all_scores) / len(all_scores) if all_scores else 0
    comparison["best_score"] = max(all_scores) if all_scores else 0
    comparison["worst_score"] = min(all_scores) if all_scores else 0
    
    return comparison

def generate_csv_export(results: Dict) -> str:
    """Generate CSV export of validation results"""
    csv_lines = ["Tool,Score,Trust Score,Warnings,Errors,Recommendations"]
    
    for tool_name, tool_result in results.items():
        warnings = "; ".join(tool_result.get("warnings", []))
        errors = "; ".join(tool_result.get("errors", []))
        recommendations = "; ".join(tool_result.get("recommendations", []))
        
        csv_lines.append(f"{tool_name},{tool_result.get('score', 0)},{tool_result.get('trust_score', '')},{warnings},{errors},{recommendations}")
    
    return "\n".join(csv_lines)

def get_tool_description(tool: ValidationTool) -> str:
    """Get description for validation tool"""
    descriptions = {
        ValidationTool.CREEPJS: "Advanced browser fingerprinting detection",
        ValidationTool.PIXELSCAN: "Hardware fingerprinting analysis",
        ValidationTool.IPHEY: "IP geolocation consistency checking",
        ValidationTool.FINGERPRINTJS: "Commercial fingerprinting service",
        ValidationTool.AMIUNIQUE: "Privacy tool effectiveness testing"
    }
    return descriptions.get(tool, "Unknown validation tool")

def get_tool_category(tool: ValidationTool) -> str:
    """Get category for validation tool"""
    categories = {
        ValidationTool.CREEPJS: "fingerprinting",
        ValidationTool.PIXELSCAN: "hardware",
        ValidationTool.IPHEY: "geolocation",
        ValidationTool.FINGERPRINTJS: "commercial",
        ValidationTool.AMIUNIQUE: "privacy"
    }
    return categories.get(tool, "unknown")
