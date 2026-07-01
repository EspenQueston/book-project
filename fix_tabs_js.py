import re
with open('manager/templates/public/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_js = '''<script>
(function(){
    var tabs = document.querySelectorAll('.na-tab');
    var panels = document.querySelectorAll('.na-tab-panel');
    tabs.forEach(function(tab){
        tab.addEventListener('click', function(){
            var target = this.getAttribute('data-panel');
            tabs.forEach(function(t){ t.classList.remove('active'); });
            panels.forEach(function(p){ p.classList.remove('active'); });
            this.classList.add('active');
            var panel = document.getElementById(target);
            if(panel) panel.classList.add('active');
        });
    });
})();
</script>'''

new_js = '''<script>
(function(){
    var tabs = document.querySelectorAll('.na-tab');
    tabs.forEach(function(tab){
        tab.addEventListener('click', function(){
            var target = this.getAttribute('data-panel');
            var container = this.closest('.new-arrivals-section') || this.closest('.featured-section');
            if (container) {
                container.querySelectorAll('.na-tab').forEach(function(t){ t.classList.remove('active'); });
                container.querySelectorAll('.na-tab-panel').forEach(function(p){ p.classList.remove('active'); });
                this.classList.add('active');
                var panel = document.getElementById(target);
                if(panel) panel.classList.add('active');
            }
        });
    });
})();
</script>'''

content = content.replace(old_js, new_js)

with open('manager/templates/public/home.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed tabs JS!')
