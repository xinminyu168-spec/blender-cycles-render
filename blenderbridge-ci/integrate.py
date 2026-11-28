from pathlib import Path
import sys
root=Path(sys.argv[1])
base=root/'standalone/src/main/java/com/droidbridge/standalone'
rust=root/'rust/crates'
edits={}
def edit(p,a,b):
    old=edits.get(p,p.read_text())
    if old.count(a)!=1: raise RuntimeError(f'Unknown anchor: {p}: {a[:80]}')
    edits[p]=old.replace(a,b,1)
def add(p,s):
    if p.exists(): raise RuntimeError(f'Already exists: {p}')
    edits[p]=s
manifest=root/'standalone/src/main/AndroidManifest.xml'
edit(manifest,'<uses-permission android:name="android.permission.INTERNET" />','<uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="com.termux.permission.RUN_COMMAND" />')
edit(manifest,'<queries>','<queries>\n        <package android:name="com.termux" />')
add(base/'blender/BlenderStarter.java', '''package com.droidbridge.standalone.blender;
import android.content.Context;
import android.content.Intent;
import android.content.ComponentName;
import android.content.pm.PackageManager;
public final class BlenderStarter {
 public static String startSupervisor(Context context) {
  if(context.checkSelfPermission("com.termux.permission.RUN_COMMAND") != PackageManager.PERMISSION_GRANTED) return "PERMISSION_REQUIRED";
  Intent i=new Intent("com.termux.RUN_COMMAND");
  i.setClassName("com.termux","com.termux.app.RunCommandService");
  i.putExtra("com.termux.RUN_COMMAND_PATH","/data/data/com.termux/files/usr/bin/bash");
  i.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",new String[]{"/data/data/com.termux/files/home/.local/bin/blenderbridge-supervisor","run"});
  i.putExtra("com.termux.RUN_COMMAND_WORKDIR","/data/data/com.termux/files/home");
  i.putExtra("com.termux.RUN_COMMAND_BACKGROUND",true);
  try { return context.startService(i)==null ? "SERVICE_NOT_AVAILABLE" : "SUBMITTED_NOT_VERIFIED"; }
  catch(SecurityException e){return "SERVICE_PERMISSION_DENIED";}
  catch(IllegalStateException e){return "ANDROID_BACKGROUND_START_BLOCKED";}
 }
}
''')
add(base/'execution/android/BlenderSupervisorAdapter.kt','''package com.droidbridge.standalone.execution.android
import android.content.Context
import com.droidbridge.standalone.blender.BlenderStarter
internal class BlenderSupervisorAdapter(private val context: Context, private val validatesFence: (String, Long, String) -> Boolean): AndroidExecutionBridge {
 override suspend fun execute(request: AndroidExecutionRequest): AndroidExecutionResult {
  if(!validatesFence(request.runtimeEpoch, request.hostGeneration, request.runtimeInstanceId)) throw AndroidExecutionException("STALE_AUTHORITY")
  if(request.primitive != AndroidPrimitive.BlenderSupervisorStart) throw AndroidExecutionException("UNSUPPORTED")
  if(request.descriptors.isNotEmpty() || !request.payload.contentEquals(byteArrayOf(123,125))) throw AndroidExecutionException("INVALID_ARGUMENT")
  return when(val status=BlenderStarter.startSupervisor(context)) {
   "SUBMITTED_NOT_VERIFIED" -> AndroidExecutionResult("{\\"submitted\\":true,\\"verified\\":false}".encodeToByteArray())
   "PERMISSION_REQUIRED", "SERVICE_PERMISSION_DENIED" -> throw AndroidExecutionException("PERMISSION_DENIED",status)
   "SERVICE_NOT_AVAILABLE", "ANDROID_BACKGROUND_START_BLOCKED" -> throw AndroidExecutionException("CAPABILITY_UNAVAILABLE",status)
   else -> throw AndroidExecutionException("IO_ERROR","UNEXPECTED_START_RESULT")
  }
 }
}
''')
edit(base/'execution/android/AndroidExecutionBridge.kt','    IntentStart,\n','    IntentStart,\n    BlenderSupervisorStart,\n')
g=base/'runtimehost/RuntimeProcessGraph.kt'
edit(g,'import com.droidbridge.standalone.execution.android.AndroidMotherToolAdapter\n','import com.droidbridge.standalone.execution.android.AndroidMotherToolAdapter\nimport com.droidbridge.standalone.execution.android.BlenderSupervisorAdapter\n')
edit(g,'            shizukuPrimitives::get,\n','            BlenderSupervisorAdapter(application, hostController::validatesFence),\n            shizukuPrimitives::get,\n')
edit(g,'            AndroidPrimitive.IntentStart,\n            AndroidPrimitive.ClipboardRead,\n            AndroidPrimitive.ClipboardWrite,\n            AndroidPrimitive.ClipboardClear,\n            AndroidPrimitive.AppProcessStart,','            AndroidPrimitive.IntentStart,\n            AndroidPrimitive.ClipboardRead,\n            AndroidPrimitive.ClipboardWrite,\n            AndroidPrimitive.ClipboardClear,\n            AndroidPrimitive.BlenderSupervisorStart,\n            AndroidPrimitive.AppProcessStart,')
edit(g,'    private val motherTool: AndroidExecutionBridge,\n','    private val motherTool: AndroidExecutionBridge,\n    private val blenderSupervisor: AndroidExecutionBridge,\n')
edit(g,'            -> motherTool.execute(request)\n','            -> motherTool.execute(request)\n            AndroidPrimitive.BlenderSupervisorStart -> blenderSupervisor.execute(request)\n')
edit(rust/'contract/src/tools.rs','pub enum AndroidIntentInput {\n','pub enum AndroidIntentInput {\n    #[serde(rename = "blender_supervisor_start")]\n    BlenderSupervisorStart {},\n')
edit(rust/'contract/src/results.rs','string_enum!(IntentOperation { View=>"view", ExplicitActivity=>"explicit_activity" });','string_enum!(IntentOperation { View=>"view", ExplicitActivity=>"explicit_activity", BlenderSupervisorStart=>"blender_supervisor_start" });')
p=rust/'runtime/src/android.rs'
edit(p,'        AndroidCall::Intent(AndroidIntentInput::View {\n','        AndroidCall::Intent(AndroidIntentInput::BlenderSupervisorStart {}) => Ok(()),\n        AndroidCall::Intent(AndroidIntentInput::View {\n')
edit(p,'            encode(match input {\n                AndroidIntentInput::View { package_name, .. } => AndroidIntentResult {','            encode(match input {\n                AndroidIntentInput::BlenderSupervisorStart {} => AndroidIntentResult {\n                    started: True,\n                    operation: IntentOperation::BlenderSupervisorStart,\n                    package_name: Some("com.termux".to_owned()),\n                    component: None,\n                },\n                AndroidIntentInput::View { package_name, .. } => AndroidIntentResult {')
edit(p,'    bridge_completed(dispatch, "IntentStart", bridge_value(input)?, execution)\n','    if matches!(input, AndroidIntentInput::BlenderSupervisorStart {}) {\n        let reply = bridge_call(dispatch, "BlenderSupervisorStart", serde_json::json!({}), execution)?;\n        let value: serde_json::Value = bridge_decode(&reply)?;\n        if value != serde_json::json!({"submitted": true, "verified": false}) {\n            return Err(DomainError::new(ErrorCode::IoError, "Blender launch acknowledgement is invalid"));\n        }\n        return Ok(());\n    }\n    bridge_completed(dispatch, "IntentStart", bridge_value(input)?, execution)\n')
edit(rust/'daemon/src/android.rs','                    AndroidIntentInput::ExplicitActivity { .. } => "start_explicit_activity",\n','                    AndroidIntentInput::ExplicitActivity { .. } => "start_explicit_activity",\n                    AndroidIntentInput::BlenderSupervisorStart {} => {\n                        return Err(clean(DomainError::new(ErrorCode::CapabilityUnavailable, "Blender supervisor requires authorized App Framework")));\n                    }\n')
for p,s in edits.items():
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s)
print("Patched",len(edits),"files; compilation required")
