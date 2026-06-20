import os
import shutil

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(workspace, 'public')
    templates_dir = os.path.join(workspace, 'templates')
    static_src = os.path.join(workspace, 'static')
    static_dst = os.path.join(public_dir, 'static')
    
    # 1. Clean existing public directory files where possible
    if os.path.exists(public_dir):
        print(f"Cleaning existing public directory: {public_dir}")
        try:
            for item in os.listdir(public_dir):
                item_path = os.path.join(public_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"Skipping locked file/folder {item}: {e}")
        except Exception as e:
            print(f"Warning during directory cleanup: {e}")
    os.makedirs(public_dir, exist_ok=True)
    
    # 2. Copy templates to public root
    templates = ['index.html', 'about_us.html', 'contact_us.html', 'privacy_policy.html', 'terms_conditions.html']
    for t in templates:
        src = os.path.join(templates_dir, t)
        dst = os.path.join(public_dir, t)
        if os.path.exists(src):
            print(f"Copying template: {t} -> public/")
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"Error copying {t}: {e}")
        else:
            print(f"Warning: Template {t} not found in {templates_dir}")
            
    # 3. Copy static folder recursively (merging into existing target)
    if os.path.exists(static_src):
        print("Copying static assets recursively -> public/static/")
        try:
            shutil.copytree(static_src, static_dst, dirs_exist_ok=True)
        except Exception as e:
            print(f"Error copying static assets: {e}")
    else:
        print(f"Warning: static folder not found in {workspace}")
        
    print("Public directory prepared successfully!")

if __name__ == '__main__':
    main()
