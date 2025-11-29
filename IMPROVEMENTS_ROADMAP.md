# Font & Styling Improvements Roadmap

---

## Current Status: 7.4/10 ✓

The EPUB conversion is **functionally excellent** but could benefit from styling enhancements.

---

## Quick Wins (Easy Fixes)

### 1. Fix Floating Point Artifacts (2 minutes)

**Current Issue:**
```html
<span style="font-size:10.500000000000014px;">Text</span>  ✗
```

**Fix:**
```python
# In src/epub_generator_v2.py, Line 379

# Change this:
style_parts = [f'font-size:{text.font_size}px', ...]

# To this:
style_parts = [f'font-size:{text.font_size:.1f}px', ...]
```

**Result:**
```html
<span style="font-size:10.5px;">Text</span>  ✓
```

**Benefit:** Clean CSS, professional appearance

---

### 2. Apply Line Heights (5 minutes)

**Current Issue:**
- Line heights are calculated in PDF extraction but never used
- Text may appear too compact

**Code Change 1:** Extract from pdf_extractor.py
```python
# pdf_extractor.py, Line 157 - Already calculating this:
line_height=y1_html - y0_html

# TextElement already stores it
```

**Code Change 2:** Apply in epub_generator_v2.py
```python
# Find line ~379, in the style_parts section:

# Current:
style_parts = [
    f'font-size:{text.font_size}px',
    'font-family:serif',
    'color:black'
]

# New:
style_parts = [
    f'font-size:{text.font_size:.1f}px',
    f'line-height:{text.line_height:.1f}px',  # Add this
    'font-family:serif',
    'color:black'
]
```

**Result:**
```html
<!-- Before -->
<span style="font-size:10.5px;font-family:serif;color:black">Text</span>

<!-- After -->
<span style="font-size:10.5px;line-height:9.5px;font-family:serif;color:black">Text</span>
```

**Benefit:** Better spacing between lines, improved readability

---

## Medium Priority Improvements

### 3. Detect Bold/Italic from Font Metrics (30 minutes)

**Current Problem:**
```python
# pdf_extractor.py:155-156
is_bold='Bold' in font_name,  # Always False (font_name is "Unknown")
is_italic='Italic' in font_name,  # Always False
```

**Why This Fails:**
- Font names are "Unknown" in this PDF
- Can't detect from name

**Solution: Use Font Metrics**

```python
# New approach - check font properties
def detect_bold_italic(char):
    """Detect bold/italic from font metrics instead of name"""

    # Get font object from pdfplumber
    font_obj = char.get('object')  # Font object

    if font_obj:
        # Check font flags
        font_flags = font_obj.get('Flags', 0)

        # Font flag meanings:
        # Bit 6 (32): Bold
        # Bit 0 (1): FixedPitch
        is_bold = bool(font_flags & 32)

        # Check italic from font name in descriptor
        font_name = str(font_obj.name) if hasattr(font_obj, 'name') else ""
        is_italic = 'Italic' in font_name or 'Oblique' in font_name

        return is_bold, is_italic

    return False, False
```

**Benefit:** Would detect bold/italic if they exist in the PDF

**Note:** Requires testing - may not work with all PDF types

---

### 4. Better Font Family Handling (45 minutes)

**Current Limitation:**
```python
# All text hardcoded to:
'font-family: serif'
```

**Option A: Detect Serif vs Sans-Serif (Simple)**
```python
def detect_font_type(char):
    """Guess font type from visual characteristics"""

    # Get character width/height ratio
    width = char.get('x1', 0) - char.get('x0', 0)
    height = char.get('y1', 0) - char.get('y0', 0)

    if width == 0 or height == 0:
        return 'serif'  # Default

    aspect_ratio = width / height

    # Typical values:
    # Serif fonts: ~0.4-0.6
    # Sans-serif: ~0.3-0.5

    # This is unreliable - not recommended
```

**Option B: Use Font Weight (Better)**
```python
def detect_font_family(char):
    """Detect font family from pdfplumber data"""

    # pdfplumber stores some metadata
    font_info = char.get('font', 'Unknown')

    # Try to extract font info:
    if 'Helvetica' in str(font_info) or 'Arial' in str(font_info):
        return 'sans-serif'
    elif 'Times' in str(font_info):
        return 'serif'
    elif 'Courier' in str(font_info):
        return 'monospace'
    else:
        return 'serif'  # Default fallback
```

**Current Verdict:** Font family detection in PDFs is unreliable. Generic 'serif' is acceptable.

---

### 5. Use CSS Classes Instead of Inline Styles (1 hour)

**Current Approach:**
```html
<span style="font-size:10.5px;font-family:serif;color:black;font-weight:bold;">Text</span>
<span style="font-size:10.5px;font-family:serif;color:black;font-weight:normal;">Text</span>
<span style="font-size:8.0px;font-family:serif;color:black;font-weight:normal;">Text</span>
```

**Better Approach:**
```html
<span class="body-text bold">Text</span>
<span class="body-text">Text</span>
<span class="small-text">Text</span>
```

With CSS:
```css
.body-text {
    font-size: 10.5px;
    font-family: serif;
    color: black;
}

.body-text.bold {
    font-weight: bold;
}

.small-text {
    font-size: 8.0px;
    font-family: serif;
    color: black;
}
```

**Benefits:**
- Smaller file size
- Easier to update styles globally
- Better readability
- Easier to maintain

**Implementation:**
```python
# In epub_generator_v2.py, create a class system

# Step 1: Identify unique style combinations
unique_styles = {}
for text in page.text_elements:
    style_key = (
        round(text.font_size, 1),
        text.is_bold,
        text.is_italic
    )
    if style_key not in unique_styles:
        unique_styles[style_key] = f"text-{len(unique_styles)}"

# Step 2: Generate CSS classes
css_rules = []
for (size, bold, italic), class_name in unique_styles.items():
    styles = [f"font-size:{size}px", "font-family:serif", "color:black"]
    if bold:
        styles.append("font-weight:bold")
    if italic:
        styles.append("font-style:italic")
    css_rules.append(f".{class_name} {{ {'; '.join(styles)}; }}")

# Step 3: Use classes in HTML
class_name = unique_styles[(round(text.font_size, 1), text.is_bold, text.is_italic)]
text_span.set('class', class_name)
```

---

## Larger Improvements

### 6. Detect and Apply Semantic Headings (2 hours)

**Current Issue:**
```html
<!-- All text is the same structure -->
<div class="Basic-Text-Frame" style="...">
  <p><span style="...">Transferring the image</span></p>
</div>
```

**Better:**
```html
<div class="heading-frame" style="...">
  <h1><span style="...">Transferring the image</span></h1>
</div>

<div class="body-text-frame" style="...">
  <p><span style="...">Body text here</span></p>
</div>
```

**Detection Logic:**
```python
def detect_heading_level(text_element):
    """Detect if text is likely a heading"""

    # Heuristics:
    size = text_element.font_size
    line_length = len(text_element.text)

    # Headings are typically:
    # - Large (>16px)
    # - Short (<100 chars)
    # - Often bold

    if size > 24:
        return 'h1'
    elif size > 18:
        return 'h2'
    elif size > 14:
        return 'h3'
    else:
        return 'p'
```

---

### 7. Group Related Text Lines into Paragraphs (2-3 hours)

**Current Issue:**
```html
<!-- Each line is separate -->
<div class="Basic-Text-Frame" style="...top:750px;...">
  <span>Line 1 text here</span>
</div>
<div class="Basic-Text-Frame" style="...top:740px;...">
  <span>Line 2 text here</span>
</div>
<div class="Basic-Text-Frame" style="...top:730px;...">
  <span>Line 3 text here</span>
</div>
```

**Better:**
```html
<div class="paragraph-frame" style="...top:750px;...height:30px;">
  <p>
    <span>Line 1 text here</span><br/>
    <span>Line 2 text here</span><br/>
    <span>Line 3 text here</span>
  </p>
</div>
```

**Algorithm:**
```python
def group_text_into_paragraphs(text_elements):
    """Group text elements that are vertically adjacent"""

    paragraphs = []
    current_paragraph = []

    for text in sorted(text_elements, key=lambda t: -t.y0):  # Top to bottom
        if not current_paragraph:
            current_paragraph.append(text)
        else:
            # Check if this text is close to previous (same line group)
            prev_y = current_paragraph[-1].y0
            gap = abs(text.y0 - prev_y)

            if gap < 15:  # Same paragraph if gap < 15px
                current_paragraph.append(text)
            else:
                # New paragraph
                paragraphs.append(current_paragraph)
                current_paragraph = [text]

    if current_paragraph:
        paragraphs.append(current_paragraph)

    return paragraphs
```

---

## Implementation Priority Matrix

| Feature | Effort | Impact | Priority | Time |
|---------|--------|--------|----------|------|
| Fix floating point | ⭐ | ⭐⭐ | 1 | 2 min |
| Apply line-heights | ⭐ | ⭐⭐ | 2 | 5 min |
| Bold/Italic detection | ⭐⭐ | ⭐⭐ | 3 | 30 min |
| CSS classes | ⭐⭐⭐ | ⭐⭐⭐ | 4 | 1 hour |
| Semantic headings | ⭐⭐⭐ | ⭐⭐ | 5 | 2 hours |
| Text grouping | ⭐⭐⭐ | ⭐⭐ | 6 | 2-3 hours |
| Embed fonts | ⭐⭐⭐⭐ | ⭐ | 7 | 4+ hours |

---

## Recommended Implementation Order

### Phase 1: Quick Fixes (10 minutes) 📋
1. ✅ Fix floating-point formatting
2. ✅ Apply line-heights from PDF

**Impact:** Better visual quality, cleaner code

### Phase 2: Detection (45 minutes) 🔍
3. Improve bold/italic detection
4. Experiment with font family detection

**Impact:** Better text styling reproduction

### Phase 3: Structure (2+ hours) 🏗️
5. Convert to CSS classes
6. Detect and apply semantic headings
7. Group text into paragraphs

**Impact:** Better EPUB semantics, smaller file size

### Phase 4: Polish (4+ hours) ✨
8. Embed fonts (if needed)
9. Test on devices
10. Fine-tune visual appearance

---

## Testing Checklist

After each improvement, verify:

- [ ] EPUB still generates without errors
- [ ] All 259 text elements present
- [ ] Positioning still accurate
- [ ] File size doesn't increase significantly
- [ ] Displays correctly in Apple Books
- [ ] Displays correctly in ePub readers (Calibre, etc.)
- [ ] CSS is valid
- [ ] XHTML is valid

---

## Quick Decision: What to Do?

### If you want to improve quality NOW:
Implement **Phase 1** (Quick Fixes) - takes 10 minutes, gives better quality

### If you want better styling:
Implement **Phase 1 + 2** (Quick Fixes + Detection) - takes ~1 hour, much better appearance

### If you want production-ready EPUB:
Implement **Phase 1 + 2 + 3** (all except fonts) - takes ~3 hours, professional quality

### If you want pixel-perfect reproduction:
Implement **all phases** - takes 5+ hours, requires font extraction and testing

---

## Current Recommendation

**For your use case, implement Phase 1 (Quick Fixes)** - they're easy, quick, and give immediate visual improvements with minimal risk.

Would you like me to implement any of these improvements?
