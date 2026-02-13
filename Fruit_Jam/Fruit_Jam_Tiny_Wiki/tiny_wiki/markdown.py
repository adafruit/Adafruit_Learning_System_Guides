# SPDX-FileCopyrightText: 2026 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Adapted from files found in tini_wiki for Micropython by Kevin McAleer:
# https://github.com/kevinmcaleer/tiny_wiki
import re

class SimpleMarkdown:
    """Lightweight markdown parser optimized for MicroPython"""

    def __init__(self):
        self.wiki_link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        self.underlines_for_bold_and_italic = False

    def parse_wiki_links(self, text, link_callback=None):
        """Parse [[PageName]] style wiki links"""
        def replace_link(match):
            page_name = match.group(1)
            if link_callback:
                return link_callback(page_name)
            return f'<a href="/wiki/{page_name}">{page_name}</a>'

        result = []
        index = 0
        while index < len(text):
            code_start = text.find('<code>', index)
            if code_start == -1:
                result.append(self.wiki_link_pattern.sub(replace_link, text[index:]))
                break
            if code_start > index:
                result.append(self.wiki_link_pattern.sub(replace_link, text[index:code_start]))
            code_end = text.find('</code>', code_start)
            if code_end == -1:
                result.append(text[code_start:])
                break
            code_end += len('</code>')
            result.append(text[code_start:code_end])
            index = code_end

        return ''.join(result)

    def to_html(self, markdown_text):
        """Convert markdown to HTML (simplified)"""
        # pylint: disable=too-many-branches, too-many-statements
        if not markdown_text:
            return ""

        html = markdown_text
        lines = html.split('\n')
        result = []
        code_blocks = []
        code_block_lines = []
        in_code_block = False
        in_list = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Code blocks
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_block_lines = []
                else:
                    in_code_block = False
                    code_html = '<pre><code>{}</code></pre>'.format('\n'.join(code_block_lines))
                    placeholder = '%%CODEBLOCK{}%%'.format(len(code_blocks))
                    code_blocks.append(code_html)
                    result.append(placeholder)
                i += 1
                continue

            if in_code_block:
                code_block_lines.append(self._escape_html(line))
                i += 1
                continue

            # Headers
            if line.startswith('# '):
                result.append('<h1>{}</h1>'.format(line[2:]))
            elif line.startswith('## '):
                result.append('<h2>{}</h2>'.format(line[3:]))
            elif line.startswith('### '):
                result.append('<h3>{}</h3>'.format(line[4:]))
            elif line.startswith('#### '):
                result.append('<h4>{}</h4>'.format(line[5:]))

            # Unordered lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append('<li>{}</li>'.format(line.strip()[2:]))

            # Close list if we were in one
            elif in_list and line.strip() == '':
                result.append('</ul>')
                in_list = False
                result.append('<br>')

            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                result.append('<hr>')

            # Paragraph
            elif line.strip():
                result.append('<p>{}</p>'.format(line))

            # Empty line
            else:
                result.append('<br>')

            i += 1

        if in_code_block:
            code_html = '<pre><code>{}</code></pre>'.format('\n'.join(code_block_lines))
            placeholder = '%%CODEBLOCK{}%%'.format(len(code_blocks))
            code_blocks.append(code_html)
            result.append(placeholder)

        # Close list if still open
        if in_list:
            result.append('</ul>')

        html = '\n'.join(result)

        # Inline formatting
        html = self._parse_inline(html)

        # Parse wiki links
        html = self.parse_wiki_links(html)

        for index, code_block in enumerate(code_blocks):
            html = html.replace('%%CODEBLOCK{}%%'.format(index), code_block)

        return html

    def _parse_inline(self, text):
        """Parse inline markdown formatting"""
        def apply_formatting(segment):
            code_spans = []

            def replace_code_span(match):
                code_text = self._escape_html(match.group(1))
                code_spans.append('<code>{}</code>'.format(code_text))
                return '%%CODESPAN{}%%'.format(len(code_spans) - 1)

            segment = re.sub(r'`([^`]+)`', replace_code_span, segment)

            # Bold: **text** or __text__
            segment = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', segment)
            if self.underlines_for_bold_and_italic:
                segment = re.sub(r'__(.+?)__', r'<strong>\1</strong>', segment)

            # Italic: *text* or _text_
            segment = re.sub(r'\*(.+?)\*', r'<em>\1</em>', segment)
            if self.underlines_for_bold_and_italic:
                segment = re.sub(r'_(.+?)_', r'<em>\1</em>', segment)

            for index, code_span in enumerate(code_spans):
                segment = segment.replace('%%CODESPAN{}%%'.format(index), code_span)

            return segment

        # Links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)

        result = []
        index = 0
        while index < len(text):
            match = re.search(r'<[^>]+>', text[index:])
            if not match:
                result.append(apply_formatting(text[index:]))
                break
            start = index + match.start()
            end = index + match.end()
            if start > index:
                result.append(apply_formatting(text[index:start]))
            result.append(text[start:end])
            index = end

        return ''.join(result)

    def _escape_html(self, text):
        """Escape HTML special characters"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        return text
