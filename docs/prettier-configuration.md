# Prettier Configuration for Meal Expense Tracker

## ✅ **Prettier Successfully Configured**

Prettier is now configured to align with your project's existing formatting standards and TIGER style principles.

### **📋 Configuration Alignment**

| **File Type**     | **Indent** | **Quotes**    | **Line Length** | **Notes**              |
| ----------------- | ---------- | ------------- | --------------- | ---------------------- |
| **HTML/Jinja2**   | 4 spaces   | Double quotes | 120 chars       | Limited Jinja2 support |
| **JavaScript/TS** | 2 spaces   | Single quotes | 120 chars       | Matches ESLint config  |
| **Python**        | 4 spaces   | Double quotes | 120 chars       | Matches Black config   |
| **JSON**          | 2 spaces   | Double quotes | 120 chars       | JSON standard          |
| **YAML**          | 2 spaces   | Single quotes | 120 chars       | Matches .editorconfig  |
| **CSS/SCSS**      | 2 spaces   | Double quotes | 120 chars       | Standard CSS           |
| **Markdown**      | 2 spaces   | -             | 80 chars        | Prose formatting       |

### **🎯 Aligned with Project Standards**

✅ **Line Length**: 120 characters (matches Black and project standard)  
✅ **Python Style**: Double quotes, 4-space indent (matches Black)  
✅ **JavaScript Style**: Single quotes, 2-space indent (matches ESLint)  
✅ **HTML Attributes**: Double quotes (HTML standard)  
✅ **EditorConfig**: Respects .editorconfig indent preferences  
✅ **TIGER Principles**: Consistent, predictable formatting

### **⚠️ Important Limitations**

**Jinja2 Templates:**

- Prettier's HTML parser doesn't understand Jinja2 syntax
- Complex templates may break formatting
- `{{ url_for('route') }}` expressions can be problematic

### **🔧 Available Commands**

```bash
# Safe HTML formatting (error pages only)
make format-html

# Hybrid approach (Prettier + djlint validation)
make format-html-hybrid

# Check HTML formatting
make lint-html

# Format all supported code
make format  # Now excludes problematic HTML formatting
```

### **🎯 Recommended Workflow**

1. **Use Prettier for**: Simple HTML, JS, CSS, JSON, YAML
2. **Use djlint for**: Jinja2 syntax validation (no formatting)
3. **Manual formatting for**: Complex Jinja2 templates

### **📁 Files Excluded from Formatting**

- `node_modules/`, `venv/`, `.git/`
- Vendor/minified files (`*.min.js`, `*.min.css`)
- Documentation with specific formatting
- Complex Jinja2 templates (by design)

### **🛡️ Safety Features**

- **Non-destructive by default**: Won't break complex templates
- **Selective formatting**: Only formats simple templates
- **Validation included**: djlint still validates Jinja2 syntax
- **Git-friendly**: Proper line endings and final newlines

### **🚀 Next Steps**

1. **Test individual files**: `npx prettier --check filename.html`
2. **Review diffs carefully**: Always check what Prettier changes
3. **Use ignore blocks**: Add `<!-- prettier-ignore -->` for complex Jinja2
4. **Consider future migration**: Watch for better Jinja2 formatters

## **Quote Style Summary**

Following your project's established quote conventions:

- **Python**: `"double quotes"` (Black enforced)
- **JavaScript**: `'single quotes'` (ESLint preferred)
- **HTML attributes**: `"double quotes"` (HTML standard)
- **Jinja2 expressions**: `'single quotes'` (Flask convention)
- **JSON**: `"double quotes"` (JSON standard)
- **YAML**: `'single quotes'` (when needed)

This configuration respects your existing codebase while providing the reliability you need after the djlint disasters! 🎉
