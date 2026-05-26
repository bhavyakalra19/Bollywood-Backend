
from django import forms
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.utils.html import format_html
from .models import Genders, Location, Post, PostApplication, Productions, SavedPost


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "state", "country", "is_active", "created_at")
	list_filter = ("is_active", "country", "state")
	search_fields = ("name", "state", "country")
	readonly_fields = ("created_at", "updated_at")
	ordering = ("name",)





# Custom widget for location_option: text input + dropdown
class LocationComboWidget(forms.Widget):
	template_name = ''  # Not using Django templates, render in render()

	def __init__(self, attrs=None, choices=()):
		super().__init__(attrs)
		self.choices = list(choices)

	def render(self, name, value, attrs=None, renderer=None):
		# Text input for typing
		text_val = ''
		if value:
			try:
				from .models import Location
				loc = Location.objects.get(pk=value)
				text_val = str(loc)
			except Exception:
				text_val = ''
		text_input = f'<input type="text" name="{name}_text" id="id_{name}_text" value="{text_val}" class="vTextField" autocomplete="off" style="width: 60%; display: inline-block;" />'
		# Dropdown for selecting
		select = f'<select name="{name}" id="id_{name}" style="width: 35%; display: inline-block; margin-left: 5px;">'
		select += '<option value="">---------</option>'
		from .models import Location
		for loc in Location.objects.all()[:100]:
			selected = ' selected' if value and str(loc.pk) == str(value) else ''
			select += f'<option value="{loc.pk}"{selected}>{loc}</option>'
		select += '</select>'
		# JS for AJAX update and autocomplete
		js = f'''
<script>
	(function($) {{
		var $text = $("#id_{name}_text");
		var $select = $("#id_{name}");
		// jQuery UI autocomplete for text input
		$text.autocomplete({{
			source: function(request, response) {{
				$.ajax({{
					url: "/admin/posts/post/location-autocomplete/",
					dataType: "json",
					data: {{ term: request.term }},
					success: function(data) {{
						response(data.results.map(function(item) {{
							return {{ label: item.text, value: item.text, id: item.id }};
						}}));
					}}
				}});
			}},
			minLength: 1,
			select: function(event, ui) {{
				// Set dropdown to match selected autocomplete
				$select.val(ui.item.id);
			}}
		}});
		// When typing, update dropdown options
		$text.on('input', function() {{
			var val = $text.val();
			$.ajax({{
				url: "/admin/posts/post/location-autocomplete/",
				dataType: "json",
				data: {{ term: val }},
				success: function(data) {{
					$select.empty();
					$select.append('<option value="">---------</option>');
					data.results.forEach(function(item) {{
						$select.append('<option value="'+item.id+'">'+item.text+'</option>');
					}});
				}}
			}});
		}});
		// When dropdown changes, update text input
		$select.on('change', function() {{
			var selectedText = $select.find('option:selected').text();
			if ($select.val()) $text.val(selectedText);
		}});
	}})(django.jQuery);
</script>
'''
		return mark_safe(text_input + select + js)

# Custom form for Post admin
class PostAdminForm(forms.ModelForm):
	class Meta:
		model = Post
		fields = [
			"title",
			"location_option",
			"phone_number",
			"min_age",
			"max_age",
			"description",
			"requirements",
			"is_active",
			"genders",
		]
		widgets = {
			'location_option': LocationComboWidget,
		}

	def clean(self):
		cleaned_data = super().clean()
		location_text = self.data.get("location_option_text")
		location_pk = cleaned_data.get("location_option")
		from .models import Location
		if location_text:
			location = Location.objects.filter(name__iexact=location_text).first()
			if not location:
				location = Location.objects.create(name=location_text, country="India")
			cleaned_data["location_option"] = location
		elif location_pk:
			# If selected from dropdown, keep as is
			pass
		else:
			cleaned_data["location_option"] = None
		return cleaned_data


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	form = PostAdminForm

	def save_model(self, request, obj, form, change):
		if not obj.created_by_id:
			obj.created_by_id = 1  # Default user ID
		super().save_model(request, obj, form, change)
	list_display = (
		"id",
		"title",
		"phone_number",
		"created_by",
		"location_option",
		"min_age",
		"max_age",
		"requirements",
		"is_active",
		"created_at",
	)
	list_filter = ("is_active", "location_option", "created_at")
	search_fields = (
		"title",
		"location_option__name",
		"location_option__state",
		"location_option__country",
		"description",
		"created_by__email",
		"created_by__phone",
	)
	autocomplete_fields = tuple()
	filter_horizontal = ("genders",)
	readonly_fields = ("created_at", "updated_at")
	ordering = ("-created_at",)

	class Media:
		js = (
			"https://code.jquery.com/ui/1.13.2/jquery-ui.min.js",
			"admin/js/location_autocomplete.js",
		)
		css = {
			'all': ("https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.css",)
		}

	def get_urls(self):
		urls = super().get_urls()
		custom_urls = [
			path("location-autocomplete/", self.admin_site.admin_view(self.location_autocomplete), name="location-autocomplete"),
		]
		return custom_urls + urls

	def location_autocomplete(self, request):
		term = request.GET.get("term", "")
		locations = Location.objects.filter(name__istartswith=term)[:10]
		results = [
			{"id": loc.id, "text": str(loc)} for loc in locations
		]
		return JsonResponse({"results": results})


@admin.register(Productions)
class ProductionsAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "created_at", "updated_at")
	search_fields = ("name",)
	readonly_fields = ("created_at", "updated_at")
	ordering = ("name",)


@admin.register(Genders)
class GendersAdmin(admin.ModelAdmin):
	list_display = ("id", "name")
	search_fields = ("name",)
	ordering = ("name",)


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "post", "created_at")
	list_filter = ("created_at",)
	search_fields = ("user__email", "user__phone", "post__title")
	autocomplete_fields = ("user", "post")
	readonly_fields = ("created_at",)
	ordering = ("-created_at",)

	def get_queryset(self, request):
		return super().get_queryset(request).select_related("user", "post")


@admin.register(PostApplication)
class PostApplicationAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "post", "created_at")
	list_filter = ("created_at",)
	search_fields = ("user__email", "user__phone", "post__title")
	autocomplete_fields = ("user", "post")
	readonly_fields = ("created_at",)
	ordering = ("-created_at",)

	def get_queryset(self, request):
		return super().get_queryset(request).select_related("user", "post")
