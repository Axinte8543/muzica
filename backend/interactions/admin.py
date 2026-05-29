from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from .models import (
	AlbumRating,
	AlbumReview,
	CorrectionReport,
	MetadataSuggestion,
	ModerationReport,
	UserSuspension,
	AnalyticsEvent,
	SensitiveActionAudit,
	SongRating,
)


@admin.action(description='Mark selected reports as resolved')
def resolve_reports(modeladmin, request, queryset):
	qs = queryset.filter(status=ModerationReport.Status.PENDING)
	for report in qs.select_related('review', 'review_comment', 'song_comment'):
		report.status = ModerationReport.Status.RESOLVED
		report.resolved_by = request.user
		report.resolved_at = timezone.now()
		report.resolution_reason = report.get_reason_code_display()
		report.resolution_feedback = report.reason or 'Raportul a fost verificat și închis de echipa de moderare.'
		report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
		SensitiveActionAudit.objects.create(
			actor=request.user,
			action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
			target_type='moderation_report',
			target_id=report.id,
			summary='Moderation report resolved in admin',
			metadata={'report_target_id': int(report.review_id or report.review_comment_id or report.song_comment_id)},
		)


@admin.action(description='Suspend reported content creator for 1 month')
def suspend_content_creator_1m(modeladmin, request, queryset):
	"""Suspend the user who created the reported content for 1 month"""
	for report in queryset.filter(status=ModerationReport.Status.PENDING):
		target_user = None
		if report.review:
			target_user = report.review.user
		elif report.review_comment:
			target_user = report.review_comment.user
		elif report.song_comment:
			target_user = report.song_comment.user
		
		if target_user:
			suspended_until = timezone.now() + timedelta(days=30)
			suspension, _ = UserSuspension.objects.get_or_create(
				user=target_user,
				is_active=True,
				defaults={
					'reason': UserSuspension.SuspensionReason.CONTENT_VIOLATION,
					'duration_type': UserSuspension.SuspensionDuration.ONE_MONTH,
					'suspended_until': suspended_until,
					'suspended_by': request.user,
					'related_report': report,
					'reason_detail': f'Content violation from report #{report.id}: {report.reason}',
				}
			)
			target_user.is_active = False
			target_user.save(update_fields=['is_active'])
			
			report.status = ModerationReport.Status.RESOLVED
			report.resolved_by = request.user
			report.resolved_at = timezone.now()
			report.resolution_reason = 'Content creator suspended'
			report.resolution_feedback = f'User {target_user.username} suspended until {suspended_until}'
			report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
			
			SensitiveActionAudit.objects.create(
				actor=request.user,
				action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
				target_type='user_suspension',
				target_id=suspension.id,
				summary=f'User {target_user.username} suspended (1 month)',
				metadata={'report_id': report.id, 'suspension_id': suspension.id},
			)
	modeladmin.message_user(request, f'Suspensions created for reported content creators', level=messages.SUCCESS)


@admin.action(description='Permanently ban reported content creator')
def ban_content_creator_permanent(modeladmin, request, queryset):
	"""Permanently ban the user who created the reported content"""
	for report in queryset.filter(status=ModerationReport.Status.PENDING):
		target_user = None
		if report.review:
			target_user = report.review.user
		elif report.review_comment:
			target_user = report.review_comment.user
		elif report.song_comment:
			target_user = report.song_comment.user
		
		if target_user:
			suspension, _ = UserSuspension.objects.get_or_create(
				user=target_user,
				is_active=True,
				defaults={
					'reason': UserSuspension.SuspensionReason.CONTENT_VIOLATION,
					'duration_type': UserSuspension.SuspensionDuration.PERMANENT,
					'suspended_until': None,
					'suspended_by': request.user,
					'related_report': report,
					'reason_detail': f'Permanent ban from report #{report.id}: {report.reason}',
				}
			)
			target_user.is_active = False
			target_user.save(update_fields=['is_active'])
			
			report.status = ModerationReport.Status.RESOLVED
			report.resolved_by = request.user
			report.resolved_at = timezone.now()
			report.resolution_reason = 'Content creator permanently banned'
			report.resolution_feedback = f'User {target_user.username} permanently banned'
			report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
			
			SensitiveActionAudit.objects.create(
				actor=request.user,
				action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
				target_type='user_suspension',
				target_id=suspension.id,
				summary=f'User {target_user.username} permanently banned',
				metadata={'report_id': report.id, 'suspension_id': suspension.id},
			)
	modeladmin.message_user(request, f'Permanent bans created for reported content creators', level=messages.SUCCESS)


@admin.register(ModerationReport)
class ModerationReportAdmin(admin.ModelAdmin):
	list_display = ('id', 'status', 'reason_code', 'target_type', 'target_display', 'reporter', 'created_at', 'resolved_by', 'resolved_at', 'action_buttons')
	list_filter = ('status', 'reason_code', 'created_at')
	search_fields = ('reason', 'reporter__username')
	ordering = ('status', '-created_at', '-id')
	actions = (resolve_reports, suspend_content_creator_1m, ban_content_creator_permanent)
	list_display_links = ('id', 'target_display')
	readonly_fields = ('created_at', 'resolved_by', 'resolved_at', 'reporter', 'target_display', 'reason_detail_display')

	fieldsets = (
		('Report Info', {
			'fields': ('reason_code', 'reason', 'reporter', 'created_at'),
		}),
		('Reported Content', {
			'fields': ('target_display', 'reason_detail_display'),
		}),
		('Resolution', {
			'fields': ('status', 'resolution_reason', 'resolution_feedback', 'resolved_by', 'resolved_at'),
		}),
	)

	@admin.display(description='Target Type')
	def target_type(self, obj: ModerationReport):
		if obj.review_id:
			return 'Review'
		if obj.review_comment_id:
			return 'Review Comment'
		if obj.song_comment_id:
			return 'Song Comment'
		return 'Unknown'

	@admin.display(description='Target')
	def target_display(self, obj: ModerationReport):
		if obj.review_id:
			return format_html(
				'<a href="/admin/interactions/albumreview/{}/change/">Review #{}</a> by {}',
				obj.review_id,
				obj.review_id,
				obj.review.user if obj.review else 'Unknown'
			)
		if obj.review_comment_id:
			return format_html(
				'<a href="/admin/interactions/reviewcomment/{}/change/">Comment #{}</a> by {}',
				obj.review_comment_id,
				obj.review_comment_id,
				obj.review_comment.user if obj.review_comment else 'Unknown'
			)
		if obj.song_comment_id:
			return format_html(
				'<a href="/admin/interactions/songcomment/{}/change/">Song Comment #{}</a> by {}',
				obj.song_comment_id,
				obj.song_comment_id,
				obj.song_comment.user if obj.song_comment else 'Unknown'
			)
		return 'Unknown target'

	@admin.display(description='Report Details')
	def reason_detail_display(self, obj: ModerationReport):
		return obj.reason or 'No details provided'

	@admin.display(description='Actions')
	def action_buttons(self, obj: ModerationReport):
		if obj.status != ModerationReport.Status.PENDING:
			return '—'
		
		resolve_url = reverse('admin:interactions_moderationreport_resolve_one', args=[obj.pk])
		suspend_url = reverse('admin:interactions_moderationreport_suspend', args=[obj.pk])
		ban_url = reverse('admin:interactions_moderationreport_ban', args=[obj.pk])
		
		return format_html(
			'<a class="button" href="{}">Resolve</a> '
			'<a class="button" style="background-color:#e8a000;" href="{}">Suspend 1M</a> '
			'<a class="button" style="background-color:#ba2121;" href="{}">Ban</a>',
			resolve_url, suspend_url, ban_url
		)

	def get_urls(self):
		urls = super().get_urls()
		custom = [
			path('resolve/<int:report_id>/', self.admin_site.admin_view(self._resolve_view), name='interactions_moderationreport_resolve_one'),
			path('suspend/<int:report_id>/', self.admin_site.admin_view(self._suspend_view), name='interactions_moderationreport_suspend'),
			path('ban/<int:report_id>/', self.admin_site.admin_view(self._ban_view), name='interactions_moderationreport_ban'),
		]
		return custom + urls

	def changelist_view(self, request, extra_context=None):
		# Default to the Pending inbox.
		if not request.GET:
			return redirect(f"{request.path}?status__exact={ModerationReport.Status.PENDING}")
		return super().changelist_view(request, extra_context=extra_context)

	def _resolve_view(self, request, report_id: int):
		if not request.user.is_staff:
			self.message_user(request, 'Forbidden', level=messages.ERROR)
			return redirect('..')
		report = get_object_or_404(ModerationReport, pk=report_id)
		if report.status == ModerationReport.Status.PENDING:
			resolution_reason = report.get_reason_code_display()
			resolution_feedback = report.reason or 'Raportul a fost verificat și închis de echipa de moderare.'
			report.status = ModerationReport.Status.RESOLVED
			report.resolved_by = request.user
			report.resolved_at = timezone.now()
			report.resolution_reason = resolution_reason
			report.resolution_feedback = resolution_feedback
			report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
			SensitiveActionAudit.objects.create(
				actor=request.user,
				action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
				target_type='moderation_report',
				target_id=report_id,
				summary='Moderation report resolved in admin',
				metadata={'report_target_id': int(report.review_id or report.review_comment_id or report.song_comment_id)},
			)
			self.message_user(request, f'Report #{report_id} resolved.', level=messages.SUCCESS)
		return redirect(request.META.get('HTTP_REFERER', '..'))

	def _suspend_view(self, request, report_id: int):
		"""Suspend content creator for 1 month"""
		if not request.user.is_staff:
			self.message_user(request, 'Forbidden', level=messages.ERROR)
			return redirect('..')
		report = get_object_or_404(ModerationReport, pk=report_id)
		
		target_user = None
		if report.review:
			target_user = report.review.user
		elif report.review_comment:
			target_user = report.review_comment.user
		elif report.song_comment:
			target_user = report.song_comment.user
		
		if target_user:
			with transaction.atomic():
				suspended_until = timezone.now() + timedelta(days=30)
				suspension, created = UserSuspension.objects.get_or_create(
					user=target_user,
					is_active=True,
					defaults={
						'reason': UserSuspension.SuspensionReason.CONTENT_VIOLATION,
						'duration_type': UserSuspension.SuspensionDuration.ONE_MONTH,
						'suspended_until': suspended_until,
						'suspended_by': request.user,
						'related_report': report,
						'reason_detail': f'Content violation from report #{report.id}: {report.reason}',
					}
				)
				target_user.is_active = False
				target_user.save(update_fields=['is_active'])
				
				report.status = ModerationReport.Status.RESOLVED
				report.resolved_by = request.user
				report.resolved_at = timezone.now()
				report.resolution_reason = 'Content creator suspended (1 month)'
				report.resolution_feedback = f'User {target_user.username} suspended until {suspended_until.strftime("%Y-%m-%d")}'
				report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
				
				SensitiveActionAudit.objects.create(
					actor=request.user,
					action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
					target_type='user_suspension',
					target_id=suspension.id,
					summary=f'User {target_user.username} suspended (1 month) from report #{report_id}',
					metadata={'report_id': report_id, 'suspension_id': suspension.id},
				)
				self.message_user(request, f'User {target_user.username} suspended for 1 month. Report resolved.', level=messages.SUCCESS)
		else:
			self.message_user(request, 'Could not identify content creator.', level=messages.ERROR)
		
		return redirect(request.META.get('HTTP_REFERER', '..'))

	def _ban_view(self, request, report_id: int):
		"""Permanently ban content creator"""
		if not request.user.is_staff:
			self.message_user(request, 'Forbidden', level=messages.ERROR)
			return redirect('..')
		report = get_object_or_404(ModerationReport, pk=report_id)
		
		target_user = None
		if report.review:
			target_user = report.review.user
		elif report.review_comment:
			target_user = report.review_comment.user
		elif report.song_comment:
			target_user = report.song_comment.user
		
		if target_user:
			with transaction.atomic():
				suspension, created = UserSuspension.objects.get_or_create(
					user=target_user,
					is_active=True,
					defaults={
						'reason': UserSuspension.SuspensionReason.CONTENT_VIOLATION,
						'duration_type': UserSuspension.SuspensionDuration.PERMANENT,
						'suspended_until': None,
						'suspended_by': request.user,
						'related_report': report,
						'reason_detail': f'Permanent ban from report #{report.id}: {report.reason}',
					}
				)
				target_user.is_active = False
				target_user.save(update_fields=['is_active'])
				
				report.status = ModerationReport.Status.RESOLVED
				report.resolved_by = request.user
				report.resolved_at = timezone.now()
				report.resolution_reason = 'Content creator permanently banned'
				report.resolution_feedback = f'User {target_user.username} permanently banned'
				report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
				
				SensitiveActionAudit.objects.create(
					actor=request.user,
					action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
					target_type='user_suspension',
					target_id=suspension.id,
					summary=f'User {target_user.username} permanently banned from report #{report_id}',
					metadata={'report_id': report_id, 'suspension_id': suspension.id},
				)
				self.message_user(request, f'User {target_user.username} permanently banned. Report resolved.', level=messages.SUCCESS)
		else:
			self.message_user(request, 'Could not identify content creator.', level=messages.ERROR)
		
		return redirect(request.META.get('HTTP_REFERER', '..'))


@admin.action(description='Approve selected suggestions')
def approve_suggestions(modeladmin, request, queryset):
	from .views import _apply_metadata_suggestion

	approved = 0
	failed = []
	for suggestion in queryset.filter(status=MetadataSuggestion.Status.PENDING).select_related('artist', 'album', 'album__artist', 'song', 'song__artist', 'song__album'):
		try:
			with transaction.atomic():
				applied = bool(_apply_metadata_suggestion(suggestion=suggestion))
				suggestion.status = MetadataSuggestion.Status.APPROVED
				suggestion.reviewed_by = request.user
				suggestion.reviewed_at = timezone.now()
				suggestion.applied = applied
				suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'applied'])
				approved += 1
		except ValueError as exc:
			failed.append(f'#{suggestion.pk}: {exc}')

	if approved:
		modeladmin.message_user(request, f'{approved} suggestion(s) approved and applied.', level=messages.SUCCESS)
	if failed:
		modeladmin.message_user(request, 'Some suggestions could not be applied: ' + '; '.join(failed), level=messages.WARNING)


@admin.action(description='Reject selected suggestions')
def reject_suggestions(modeladmin, request, queryset):
	qs = queryset.filter(status=MetadataSuggestion.Status.PENDING)
	qs.update(status=MetadataSuggestion.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now())


@admin.register(MetadataSuggestion)
class MetadataSuggestionAdmin(admin.ModelAdmin):
	list_display = ('id', 'status', 'kind', 'target_summary', 'suggester', 'created_at', 'applied', 'reviewed_by', 'reviewed_at', 'approve_one_click', 'reject_one_click')
	list_filter = ('status', 'kind', 'created_at', 'applied')
	search_fields = ('note', 'decision_note', 'suggester__username')
	ordering = ('status', '-created_at', '-id')
	actions = (approve_suggestions, reject_suggestions)
	list_display_links = ('id', 'target_summary')

	@admin.display(description='Target')
	def target_summary(self, obj: MetadataSuggestion):
		if obj.artist_id:
			return f"artist:{obj.artist_id}"
		if obj.album_id:
			return f"album:{obj.album_id}"
		return f"song:{obj.song_id}"

	@admin.display(description='Approve', boolean=False)
	def approve_one_click(self, obj: MetadataSuggestion):
		if obj.status != MetadataSuggestion.Status.PENDING:
			return '-'
		url = reverse('admin:interactions_metadatasuggestion_approve_one', args=[obj.pk])
		return format_html('<a class="button" href="{}">Approve</a>', url)

	@admin.display(description='Reject', boolean=False)
	def reject_one_click(self, obj: MetadataSuggestion):
		if obj.status != MetadataSuggestion.Status.PENDING:
			return '-'
		url = reverse('admin:interactions_metadatasuggestion_reject_one', args=[obj.pk])
		return format_html('<a class="button" href="{}">Reject</a>', url)

	def get_urls(self):
		urls = super().get_urls()
		custom = [
			path('approve/<int:suggestion_id>/', self.admin_site.admin_view(self._approve_view), name='interactions_metadatasuggestion_approve_one'),
			path('reject/<int:suggestion_id>/', self.admin_site.admin_view(self._reject_view), name='interactions_metadatasuggestion_reject_one'),
		]
		return custom + urls

	def changelist_view(self, request, extra_context=None):
		# Default to the Pending inbox.
		if not request.GET:
			return redirect(f"{request.path}?status__exact={MetadataSuggestion.Status.PENDING}")
		return super().changelist_view(request, extra_context=extra_context)

	def _approve_view(self, request, suggestion_id: int):
		if not request.user.is_staff:
			self.message_user(request, 'Forbidden', level=messages.ERROR)
			return redirect('..')
		s = get_object_or_404(MetadataSuggestion, pk=suggestion_id)
		if s.status == MetadataSuggestion.Status.PENDING:
			from .views import _apply_metadata_suggestion

			try:
				with transaction.atomic():
					applied = bool(_apply_metadata_suggestion(suggestion=s))
					s.status = MetadataSuggestion.Status.APPROVED
					s.reviewed_by = request.user
					s.reviewed_at = timezone.now()
					s.applied = applied
					s.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'applied'])
					SensitiveActionAudit.objects.create(
						actor=request.user,
						action_type=SensitiveActionAudit.ActionType.METADATA_SUGGESTION_DECIDED,
						target_type='metadata_suggestion',
						target_id=s.pk,
						summary='Metadata suggestion approved in admin',
						metadata={'decision': 'approve', 'applied': applied, 'kind': s.kind},
					)
				self.message_user(request, f'Suggestion #{suggestion_id} approved and applied.', level=messages.SUCCESS)
			except ValueError as exc:
				self.message_user(request, f'Cannot approve suggestion #{suggestion_id}: {exc}', level=messages.ERROR)
		return redirect(request.META.get('HTTP_REFERER', '..'))

	def _reject_view(self, request, suggestion_id: int):
		if not request.user.is_staff:
			self.message_user(request, 'Forbidden', level=messages.ERROR)
			return redirect('..')
		s = get_object_or_404(MetadataSuggestion, pk=suggestion_id)
		if s.status == MetadataSuggestion.Status.PENDING:
			s.status = MetadataSuggestion.Status.REJECTED
			s.reviewed_by = request.user
			s.reviewed_at = timezone.now()
			s.applied = False
			s.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'applied'])
			SensitiveActionAudit.objects.create(
				actor=request.user,
				action_type=SensitiveActionAudit.ActionType.METADATA_SUGGESTION_DECIDED,
				target_type='metadata_suggestion',
				target_id=s.pk,
				summary='Metadata suggestion rejected in admin',
				metadata={'decision': 'reject', 'kind': s.kind},
			)
			self.message_user(request, f'Suggestion #{suggestion_id} rejected.', level=messages.SUCCESS)
		return redirect(request.META.get('HTTP_REFERER', '..'))


@admin.register(CorrectionReport)
class CorrectionReportAdmin(admin.ModelAdmin):
	list_display = ('id', 'created_at', 'user', 'page_url')
	list_filter = ('created_at',)
	search_fields = ('page_url', 'description', 'user__username')
	ordering = ('-created_at', '-id')


@admin.register(UserSuspension)
class UserSuspensionAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'reason', 'duration_type', 'suspended_at', 'suspended_until', 'is_active', 'suspended_by', 'is_expired_display')
	list_filter = ('is_active', 'reason', 'duration_type', 'suspended_at')
	search_fields = ('user__username', 'reason_detail', 'appeal_reason')
	readonly_fields = ('suspended_at', 'suspended_by', 'related_report')
	ordering = ('-suspended_at', '-id')

	fieldsets = (
		('Suspension Info', {
			'fields': ('user', 'is_active', 'reason', 'reason_detail'),
		}),
		('Duration', {
			'fields': ('duration_type', 'suspended_at', 'suspended_until'),
		}),
		('Moderator Info', {
			'fields': ('suspended_by', 'related_report'),
		}),
		('Appeal', {
			'fields': ('appeal_at', 'appeal_reason', 'appealed_by_user'),
		}),
	)

	@admin.display(description='Expired?', boolean=True)
	def is_expired_display(self, obj: UserSuspension):
		return obj.is_expired

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.select_related('user', 'suspended_by', 'related_report')


@admin.register(SensitiveActionAudit)
class SensitiveActionAuditAdmin(admin.ModelAdmin):
	list_display = ('id', 'created_at', 'action_type', 'actor', 'target_type', 'target_id', 'summary')
	list_filter = ('action_type', 'created_at')
	search_fields = ('summary', 'target_type', 'actor__username')
	ordering = ('-created_at', '-id')


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
	list_display = ('id', 'created_at', 'event_name', 'user', 'target_type', 'target_id')
	list_filter = ('event_name', 'target_type', 'created_at')
	search_fields = ('event_name', 'target_type', 'user__username')
	ordering = ('-created_at', '-id')


admin.site.register(AlbumRating)
admin.site.register(SongRating)
admin.site.register(AlbumReview)
