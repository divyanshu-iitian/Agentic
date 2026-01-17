# Example Tasks

## Desktop Automation

### Simple Calculator Tasks

```
open calculator and compute 15% of 50000
```

**Expected Steps**:
1. `open_app` → calculator
2. `wait` → 1 second
3. `type` → "50000*0.15"
4. `stop`

---

```
open calculator and add 1234 and 5678
```

**Expected Steps**:
1. `open_app` → calculator
2. `wait` → 1 second
3. `type` → "1234+5678"
4. `stop`

---

### Notepad Tasks

```
open notepad and type hello world
```

**Expected Steps**:
1. `open_app` → notepad
2. `wait` → 1 second
3. `type` → "hello world"
4. `stop`

---

```
open notepad and write today's date
```

**Expected Steps**:
1. `open_app` → notepad
2. `wait` → 1 second
3. `type` → "January 15, 2026" (or current date)
4. `stop`

---

## Browser Automation

### Search Tasks

```
search best laptop under 80000 INR
```

**Expected Steps**:
1. `browser_open` → https://www.google.com
2. `browser_search` → "best laptop under 80000 INR"
3. `stop`

---

```
search Python async tutorial
```

**Expected Steps**:
1. `browser_open` → https://www.google.com
2. `browser_search` → "Python async tutorial"
3. `stop`

---

### Information Extraction

```
search best laptop under 80k and summarize
```

**Expected Steps**:
1. `browser_open` → https://www.google.com
2. `browser_search` → "best laptop under 80000"
3. `browser_scroll` → 1200
4. `browser_extract` → "top recommended laptops with specs"
5. `stop`

---

```
go to github trending and extract top repos
```

**Expected Steps**:
1. `browser_open` → https://github.com/trending
2. `wait` → 2 seconds
3. `browser_extract` → "top trending repositories"
4. `stop`

---

### Navigation Tasks

```
go to stackoverflow and search for Python decorators
```

**Expected Steps**:
1. `browser_open` → https://stackoverflow.com
2. `wait` → 2 seconds
3. `browser_click` → search box
4. `type` → "Python decorators"
5. `stop`

---

## Combined Tasks

```
search Python tutorial, scroll down, and extract the first 3 links
```

**Expected Steps**:
1. `browser_open` → https://www.google.com
2. `browser_search` → "Python tutorial"
3. `browser_scroll` → 800
4. `browser_extract` → "first 3 tutorial links"
5. `stop`

---

## Advanced Examples (Future)

These will work better in Phase 2 with improved planning:

```
search for weather in Mumbai and save it to notepad
```

```
go to my email, extract unread count, and tell me
```

```
find the cheapest flight to Bangalore on Google Flights
```

```
download the latest Python version installer
```

---

## Task Design Guidelines

### ✅ Good Tasks

**Characteristics**:
- Clear, specific goal
- Limited scope (3-5 steps)
- Observable outcome
- Uses whitelisted apps/domains

**Examples**:
- "search X and summarize"
- "open calculator and compute X"
- "go to Y and extract Z"

---

### ❌ Bad Tasks

**Characteristics**:
- Vague or ambiguous
- Requires many steps
- Involves sensitive data
- Uses blocked apps/domains

**Examples**:
- "do my homework" (too vague)
- "install software" (blocked)
- "delete all files" (dangerous)
- "login to my bank" (sensitive)

---

## Testing New Tasks

### 1. Start Simple

Begin with single-step tasks:
```
open notepad
```

### 2. Add Complexity

Add one action at a time:
```
open notepad and type hello
```

### 3. Test Variations

Try different phrasings:
```
launch notepad and write hello
```

### 4. Check Logs

Review `logs/agent.log` to see:
- What actions were chosen
- Why actions failed (if any)
- JSON output from LLM

### 5. Adjust Config

If needed, modify:
- `config.yaml` → Add to whitelist
- `llm/prompt.py` → Improve examples

---

## Debugging Failed Tasks

### Task: "open calculator and compute 15% of 50000"

**Symptom**: Agent stops after opening calculator

**Debug Steps**:
1. Check `logs/agent.log` for last action
2. Check `state/action_history.json` for sequence
3. Look at LLM output: Did it generate correct JSON?

**Possible Issues**:
- Calculator didn't open (app name wrong)
- LLM generated invalid JSON
- Timeout too short

**Solutions**:
- Update app name in `desktop_executor.py`
- Improve system prompt examples
- Increase wait time in config

---

### Task: "search best laptop"

**Symptom**: Browser opens but doesn't search

**Debug Steps**:
1. Check if Google is whitelisted in `config.yaml`
2. Check browser executor logs
3. Verify network connection

**Possible Issues**:
- Domain blocked by whitelist
- Browser timeout
- Network error

**Solutions**:
- Add domain to `allowed_domains`
- Increase `default_timeout`
- Check internet connection

---

## Performance Tips

### Speed Up Execution

1. **Use smaller LLM**:
   ```yaml
   llm:
     model: "llama3.2:3b"  # Faster than 7B models
   ```

2. **Disable OCR**:
   ```yaml
   observation:
     ocr_enabled: false
   ```

3. **Reduce delays**:
   ```yaml
   execution:
     desktop:
       click_delay: 0.2
   ```

### Improve Reliability

1. **Enable screenshots**:
   ```yaml
   execution:
     desktop:
       screenshot_before_click: true
   ```

2. **Increase timeouts**:
   ```yaml
   execution:
     browser:
       default_timeout: 20000
   ```

3. **Use specific prompts**:
   - Instead of: "search laptop"
   - Use: "search best laptop under 80000 INR on Google"

---

## Contributing Examples

Have a cool task the agent can perform? Add it here!

**Format**:
```markdown
### Category

Task description in natural language

Expected steps:
1. action → details
2. action → details
...
```

Submit via pull request to help the community!

---

## Task Benchmark Suite (Future)

Standard tasks for testing agent performance:

1. **Desktop-01**: Open calculator, compute simple math
2. **Desktop-02**: Open notepad, type text, close
3. **Browser-01**: Search Google, extract top result
4. **Browser-02**: Navigate to specific site, click element
5. **Combined-01**: Search, extract, save to notepad

Success rate target: 90% by Phase 2

---

**Last Updated**: January 15, 2026
