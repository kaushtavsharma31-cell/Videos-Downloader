import os
import shutil

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(workspace, 'public')
    templates_dir = os.path.join(workspace, 'templates')
    static_src = os.path.join(workspace, 'static')
    static_dst = os.path.join(public_dir, 'static')
    
    # 1. Recreate clean public directory
    if os.path.exists(public_dir):
        print(f"Cleaning existing public directory: {public_dir}")
        shutil.rmtree(public_dir)
    os.makedirs(public_dir, exist_ok=True)
    
    # 2. Copy templates to public root
    templates = ['index.html', 'about_us.html', 'contact_us.html', 'privacy_policy.html', 'terms_conditions.html']
    for t in templates:
        src = os.path.join(templates_dir, t)
        dst = os.path.join(public_dir, t)
        if os.path.exists(src):
            print(f"Copying template: {t} -> public/")
            shutil.copy2(src, dst)
        else:
            print(f"Warning: Template {t} not found in {templates_dir}")
            
    # 3. Copy static folder recursively
    if os.path.exists(static_src):
        print("Copying static assets recursively -> public/static/")
        shutil.copytree(static_src, static_dst)
    else:
        print(f"Warning: static folder not found in {workspace}")
        
    print("Public directory prepared successfully!")

if __name__ == '__main__':
    main()
