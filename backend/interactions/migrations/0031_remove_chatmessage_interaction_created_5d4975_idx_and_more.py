                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0030_albumreviewreaction'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='albumreviewreaction',
            new_name='interaction_review__ad9aab_idx',
            old_name='interaction_review_i_32cb42_idx',
        ),
        migrations.RenameIndex(
            model_name='albumreviewreaction',
            new_name='interaction_user_id_f0e762_idx',
            old_name='interaction_user_id_dfbf97_idx',
        ),
        migrations.RenameIndex(
            model_name='chatmessage',
            new_name='interaction_sender__121cc1_idx',
            old_name='chat_msg_sender_recipient_idx',
        ),
        migrations.RenameIndex(
            model_name='chatmessage',
            new_name='interaction_recipie_cd15ab_idx',
            old_name='chat_msg_recipient_unread_idx',
        ),
        migrations.RenameIndex(
            model_name='reviewcommentreaction',
            new_name='interaction_comment_a2e76a_idx',
            old_name='interactions_reviewc_comment_69d8c6_idx',
        ),
        migrations.RenameIndex(
            model_name='reviewcommentreaction',
            new_name='interaction_user_id_ab471b_idx',
            old_name='interactions_reviewc_user_id_f8b2a7_idx',
        ),
        migrations.RenameIndex(
            model_name='songcomment',
            new_name='interaction_parent__01d5d1_idx',
            old_name='songcomment_parent_created_idx',
        ),
        migrations.RenameIndex(
            model_name='songcommentreaction',
            new_name='interaction_comment_7b834b_idx',
            old_name='interactions_songc_comment_8f9c2e_idx',
        ),
        migrations.RenameIndex(
            model_name='songcommentreaction',
            new_name='interaction_user_id_794a58_idx',
            old_name='interactions_songc_user_id_c4a8e9_idx',
        ),
        migrations.AlterField(
            model_name='metadatasuggestion',
            name='kind',
            field=models.CharField(choices=[('release_date', 'Release date'), ('cover_url', 'Cover URL'), ('image_url', 'Artist image'), ('tracklist', 'Tracklist'), ('bio', 'Bio'), ('aliases', 'Aliases'), ('description', 'Description'), ('other', 'Other')], max_length=32),
        ),
    ]
