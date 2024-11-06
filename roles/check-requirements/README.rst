Check that a project's requirements match the global requirements repo.

**Role Variables**

.. zuul:rolevar:: zuul_work_dir
   :default: {{ zuul.project.src_dir }}

   Directory holding the project to check.

.. zuul:rolevar:: zuul_branch
   :default: {{ zuul.branch }}

   Branch to check.
